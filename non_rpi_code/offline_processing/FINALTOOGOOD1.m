% Eddy Current - Physical Triplet Shape Detector & Target Sizer
% WITH HYSTERESIS CORRECTION AND ROBUST NON-MAXIMUM SUPPRESSION
clear; clc; close all;

%% 1. Configuration
target_folder = 'heatmap4'; % CHANGE TO heatmap4 FOR THE SECOND RUN
target_mag = 'magnitude_h2'; 

% TUNABLE PARAMETER: Hysteresis / Lag Correction
sensor_lag_samples = 6; 

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

%% 3. Build the Physical Spatial Template (The 12cm Triplet)
x_k = -8 : grid_res : 8; 
triplet_template = exp(-(x_k).^2 / 2) + ...
                   0.5 * exp(-(x_k - 4.0).^2 / 2) + ...
                   0.5 * exp(-(x_k + 4.0).^2 / 2);
triplet_template = triplet_template - mean(triplet_template);

%% 4. Directional Shape Detection & Robust NMS
V_presence_stack = zeros(size(Xq, 1), size(Xq, 2), length(valid_files));
V_raw_stack = zeros(size(Xq, 1), size(Xq, 2), length(valid_files)); % NEW: Save Raw Data
flight_mask = true(size(Xq)); 

for i = 1:length(valid_files)
    T = readtable(valid_files{i});
    x = T.x_m * 100; y = T.y_m * 100; mag = T.(target_mag);
    
    % --- LAG CORRECTION (Hysteresis Fix) ---
    if length(x) > sensor_lag_samples
        x = x(1 : end - sensor_lag_samples);
        y = y(1 : end - sensor_lag_samples);
        mag = mag(sensor_lag_samples + 1 : end);
    end
    
    F = scatteredInterpolant(x, y, mag, 'linear', 'none');
    V_layer = F(Xq, Yq);
    
    flight_mask = flight_mask & isnan(V_layer);
    
    % NEW: Save the raw un-convoluted magnitude map before altering V_layer
    V_raw_stack(:,:,i) = V_layer;
    
    V_layer(isnan(V_layer)) = median(mag); 
    
    dist_x = sum(abs(diff(x))); dist_y = sum(abs(diff(y)));
    
    if dist_x > dist_y
        fprintf('File %d (X-Sweep): Extracting vertical ridges...\n', i);
        V_match = conv2(V_layer, triplet_template, 'same');
        V_match(V_match < 0) = 0; 
        V_smooth = imgaussfilt(V_match, 1.0);
        
        V_left = [V_smooth(:, 1), V_smooth(:, 1:end-1)];
        V_right = [V_smooth(:, 2:end), V_smooth(:, end)];
        is_max = (V_smooth >= V_left) & (V_smooth >= V_right) & (V_match > 0);
        V_match = V_match .* is_max;
        
    else
        fprintf('File %d (Y-Sweep): Extracting horizontal ridges...\n', i);
        V_match = conv2(V_layer, triplet_template', 'same');
        V_match(V_match < 0) = 0; 
        V_smooth = imgaussfilt(V_match, 1.0);
        
        V_up = [V_smooth(1, :); V_smooth(1:end-1, :)];
        V_down = [V_smooth(2:end, :); V_smooth(end, :)];
        is_max = (V_smooth >= V_up) & (V_smooth >= V_down) & (V_match > 0);
        V_match = V_match .* is_max;
    end
    
    V_match = imdilate(V_match, strel('square', 3));
    V_presence_stack(:,:,i) = imgaussfilt(V_match, 0.5);
end

%% 5. Merge and Format Presence Map
V_final_presence = max(V_presence_stack, [], 3);
V_final_raw = max(V_raw_stack, [], 3); % NEW: Merge Raw Data

% Normalization for Presence Map
valid_vals = sort(V_final_presence(V_final_presence > 0.01));
if ~isempty(valid_vals)
    idx_99 = max(1, round(0.995 * length(valid_vals)));
    robust_max = valid_vals(idx_99);
    if robust_max < 1e-6
        robust_max = max(V_final_presence(:)); 
    end
    V_final_presence = (V_final_presence / robust_max) * 100;
end
V_final_presence(V_final_presence > 100) = 100; 
V_final_presence(V_final_presence < 20) = 0;    
V_final_presence(flight_mask) = NaN; 
V_final_presence(V_final_presence == 0) = NaN; 

% NEW: Create Sizing Map by masking Raw Data with the Presence Lines
rebar_mask = (V_final_presence >= 30); % Only look where we are confident a bar exists
V_final_sizing = V_final_raw .* rebar_mask;
V_final_sizing(V_final_sizing == 0) = NaN;

%% 6. Render Figure 1: Geometry (Presence)
figure('Name', 'Stage 1: Triplet Presence Map (Geometry)', 'Position', [100, 100, 900, 750]);
pcolor(Xq, Yq, V_final_presence); 
shading interp; 
colormap(gca, turbo); 
cb = colorbar;
ylabel(cb, 'Shape Match Confidence (%)', 'FontSize', 12, 'FontWeight', 'bold');
title('Stage 1: Target Presence Map (Geometry & Location)', 'FontSize', 14);
xlabel('X Position (cm)', 'FontSize', 12); 
ylabel('Y Position (cm)', 'FontSize', 12);
axis equal tight; 
grid on; 
set(gca, 'Color', [0.02 0.02 0.1], 'FontSize', 11);

%% 7. Render Figure 2: Sizing (Raw Magnitude)
figure('Name', 'Stage 2: Triplet Sizing Map (Magnitude)', 'Position', [1050, 100, 900, 750]);
pcolor(Xq, Yq, V_final_sizing); 
shading interp; 
colormap(gca, hot); % Using 'hot' to emphasize raw signal strength
cb2 = colorbar;
ylabel(cb2, 'Peak Harmonic Magnitude', 'FontSize', 12, 'FontWeight', 'bold');
title('Stage 2: Target Sizing Map (Raw Magnitude Classification)', 'FontSize', 14);
xlabel('X Position (cm)', 'FontSize', 12); 
ylabel('Y Position (cm)', 'FontSize', 12);
axis equal tight; 
grid on; 
set(gca, 'Color', [0.02 0.02 0.1], 'FontSize', 11);