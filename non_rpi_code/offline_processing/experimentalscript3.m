% Eddy Current - Raw Aligned Magnitude vs. Processed Presence Map
clear; clc; close all;

%% 1. Configuration
target_folder = 'heatmap4';
target_mag = 'magnitude_h2'; 

% 17-packet Vicon/Sensor transmission delay compensation
sync_delay_samples = 17; 

if ~isfolder(target_folder)
    error('Folder %s not found. Run from parent directory.', target_folder);
end

files = dir(fullfile(target_folder, '*.csv'));
valid_files = {};
for i = 1:length(files)
    if contains(files(i).name, '_h0') || contains(files(i).name, '_h1') || ...
       contains(files(i).name, '_h2') || contains(files(i).name, '_h3')
        continue; 
    end
    valid_files{end+1} = fullfile(target_folder, files(i).name);
end

%% 2. Global Boundaries & Spatial Grid (0.5cm)
all_x = []; all_y = [];
for i = 1:length(valid_files)
    T = readtable(valid_files{i});
    all_x = [all_x; T.x_m * 100]; all_y = [all_y; T.y_m * 100];
end

grid_res = 0.5; 
[Xq, Yq] = meshgrid(floor(min(all_x)):grid_res:ceil(max(all_x)), ...
                    floor(min(all_y)):grid_res:ceil(max(all_y)));

%% 3. Build the Physical Spatial Template (For Processed Map)
x_k = -8 : grid_res : 8; 
triplet_template = exp(-(x_k).^2 / 2) + ...
                   0.5 * exp(-(x_k - 4.0).^2 / 2) + ...
                   0.5 * exp(-(x_k + 4.0).^2 / 2);
triplet_template = triplet_template - mean(triplet_template);

%% 4. Data Pipeline (Raw Stacking & Shape Detection)
V_raw_stack = zeros(size(Xq, 1), size(Xq, 2), length(valid_files));
V_presence_stack = zeros(size(Xq, 1), size(Xq, 2), length(valid_files));
flight_mask = true(size(Xq)); 

for i = 1:length(valid_files)
    T = readtable(valid_files{i});
    x = T.x_m * 100; y = T.y_m * 100; mag = T.(target_mag);
    
    % Apply 17-packet Phase-Lag Compensation to straighten the zig-zag
    if length(mag) > sync_delay_samples
        mag_corrected = [mag(sync_delay_samples + 1 : end); zeros(sync_delay_samples, 1)];
    else
        mag_corrected = mag;
    end
    
    F = scatteredInterpolant(x, y, mag_corrected, 'linear', 'none');
    V_layer = F(Xq, Yq);
    
    flight_mask = flight_mask & isnan(V_layer);
    
    % --- STORE THE PURE RAW DATA ---
    % Keep the unadulterated magnitude (NaNs intact for now) to merge later
    V_raw_stack(:,:,i) = V_layer;
    
    % Neutralize empty space for convolution
    V_layer(isnan(V_layer)) = median(mag_corrected); 
    
    % Determine Phase Sweep Direction for processing
    dist_x = sum(abs(diff(x))); dist_y = sum(abs(diff(y)));
    
    if dist_x > dist_y
        V_match_raw = conv2(V_layer, triplet_template, 'same');
    else
        V_match_raw = conv2(V_layer, triplet_template', 'same');
    end
    
    V_match_rect = V_match_raw;
    V_match_rect(V_match_rect < 0) = 0; 
    
    % Light smoothing for the processed map
    V_presence_stack(:,:,i) = imgaussfilt(V_match_rect, 1.5);
end

%% 5. Merge and Format Both Maps

% --- MAP 1: RAW MAGNITUDE MERGE ---
% Max merge ensures strong axis hits overwrite weak axis parallel noise
V_final_raw = max(V_raw_stack, [], 3);
V_final_raw(flight_mask) = NaN; % Clean the background

% --- MAP 2: PROCESSED PRESENCE MERGE ---
V_final_presence = max(V_presence_stack, [], 3);
V_final_presence = (V_final_presence / max(V_final_presence(:))) * 100;
V_final_presence(V_final_presence < 20) = 0; % Thresholding
V_final_presence(flight_mask) = NaN; 
V_final_presence(V_final_presence == 0) = NaN; 

%% 6. Render Map 1: Pure Raw Aligned Magnitude
figure('Name', 'RAW SENSOR DATA (Aligned)', 'Position', [100, 100, 800, 700]);
pcolor(Xq, Yq, V_final_raw); 
shading flat; % Quantized squares
colormap(gca, turbo);

cb1 = colorbar;
ylabel(cb1, 'Raw Magnetic Magnitude', 'FontSize', 12, 'FontWeight', 'bold');

title('Raw Sensor Output (Latency Aligned)', 'FontSize', 14);
xlabel('X Position (cm)', 'FontSize', 12); 
ylabel('Y Position (cm)', 'FontSize', 12);

axis equal tight; 
grid on; 
set(gca, 'Color', [0.02 0.02 0.1], 'FontSize', 11);

%% 7. Render Map 2: Processed Shape Presence
figure('Name', 'PROCESSED TARGET OCCUPANCY', 'Position', [920, 100, 800, 700]);
pcolor(Xq, Yq, V_final_presence); 
shading flat; % Quantized squares
colormap(gca, turbo);

cb2 = colorbar;
ylabel(cb2, 'Shape Match Confidence (%)', 'FontSize', 12, 'FontWeight', 'bold');

title('Target Occupancy Grid (Shape Detector)', 'FontSize', 14);
xlabel('X Position (cm)', 'FontSize', 12); 
ylabel('Y Position (cm)', 'FontSize', 12);

axis equal tight; 
grid on; 
set(gca, 'Color', [0.02 0.02 0.1], 'FontSize', 11);