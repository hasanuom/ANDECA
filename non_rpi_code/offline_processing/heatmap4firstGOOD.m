% Eddy Current - Physical Triplet Shape Detector (Presence Mapping)
clear; clc; close all;

%% 1. Configuration
target_folder = 'heatmap4';
target_mag = 'magnitude_h2'; 

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
% Create a physical axis from -8cm to +8cm
x_k = -8 : grid_res : 8; 

% Synthesize the exact geometry of the D-Coil perpendicular hit:
% Center peak (amplitude 1) + Two side peaks at +/- 4cm (amplitude 0.5)
triplet_template = exp(-(x_k).^2 / 2) + ...
                   0.5 * exp(-(x_k - 4.0).^2 / 2) + ...
                   0.5 * exp(-(x_k + 4.0).^2 / 2);

% Make it zero-mean. This forces it to act as a pure shape-matching 
% algorithm, ignoring underlying baseline magnitude.
triplet_template = triplet_template - mean(triplet_template);

%% 4. Directional Shape Detection
V_presence_stack = zeros(size(Xq, 1), size(Xq, 2), length(valid_files));
flight_mask = true(size(Xq)); 

for i = 1:length(valid_files)
    T = readtable(valid_files{i});
    x = T.x_m * 100; y = T.y_m * 100; mag = T.(target_mag);
    
    F = scatteredInterpolant(x, y, mag, 'linear', 'none');
    V_layer = F(Xq, Yq);
    
    flight_mask = flight_mask & isnan(V_layer);
    
    % Neutralize empty space with the baseline median to prevent edge-ringing
    V_layer(isnan(V_layer)) = median(mag); 
    
    % Determine Phase Sweep Direction 
    dist_x = sum(abs(diff(x))); dist_y = sum(abs(diff(y)));
    
    if dist_x > dist_y
        % X-Sweep (Crossing Vertical Bars)
        % Slide the 1D triplet shape horizontally across every row.
        fprintf('File %d (X-Sweep): Scanning rows for 3-peak vertical geometry...\n', i);
        V_match = conv2(V_layer, triplet_template, 'same');
    else
        % Y-Sweep (Crossing Horizontal Bars)
        % Slide the 1D triplet shape vertically down every column.
        fprintf('File %d (Y-Sweep): Scanning columns for 3-peak horizontal geometry...\n', i);
        V_match = conv2(V_layer, triplet_template', 'same');
    end
    
    % Rectify: Delete negative match scores (this instantly kills the M-Shape parallel hits)
    V_match(V_match < 0) = 0; 
    
    % Smooth slightly to connect the manual scan gaps
    V_presence_stack(:,:,i) = imgaussfilt(V_match, 1.5);
end

%% 5. Merge and Format Presence Map
% Stack the phases. Parallel sweeps yielded a 0 match score, so they 
% are safely ignored during the max() merge.
V_final_presence = max(V_presence_stack, [], 3);

% Normalize to a 0-100% "Confidence of Presence" scale
V_final_presence = (V_final_presence / max(V_final_presence(:))) * 100;

% Threshold: Only plot pixels where the shape match is > 20%
V_final_presence(V_final_presence < 20) = 0;

V_final_presence(flight_mask) = NaN; 
V_final_presence(V_final_presence == 0) = NaN; 

%% 6. Render Binary-Style Map
figure('Name', 'Physical Triplet Presence Map', 'Position', [100, 100, 900, 750]);

pcolor(Xq, Yq, V_final_presence); 
shading interp; 
colormap(gca, turbo); % Turbo provides distinct separation for confidence levels

cb = colorbar;
ylabel(cb, 'Shape Match Confidence (%)', 'FontSize', 12, 'FontWeight', 'bold');

title('Target Presence Map (Physical Shape Detector)', 'FontSize', 14);
xlabel('X Position (cm)', 'FontSize', 12); 
ylabel('Y Position (cm)', 'FontSize', 12);

axis equal tight; 
grid on; 
set(gca, 'Color', [0.02 0.02 0.1], 'FontSize', 11);