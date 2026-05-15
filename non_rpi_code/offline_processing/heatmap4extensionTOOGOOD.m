% Eddy Current - Physical Triplet Shape Detector (Presence Mapping)
% WITH HYSTERESIS CORRECTION AND ROBUST NON-MAXIMUM SUPPRESSION
clear; clc; close all;

%% 1. Configuration
target_folder = 'heatmap2';
target_mag = 'magnitude_h2'; 

% =========================================================================
% TUNABLE PARAMETER: Hysteresis / Lag Correction
% Adjust this to align the zig-zag. Shifts magnitude backward in time to
% correct for Time-of-Flight sensor delay.
sensor_lag_samples = 6; 
% =========================================================================

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
flight_mask = true(size(Xq)); 

for i = 1:length(valid_files)
    T = readtable(valid_files{i});
    x = T.x_m * 100; y = T.y_m * 100; mag = T.(target_mag);
    
    % --- LAG CORRECTION (Hysteresis Fix) ---
    % Shifts magnitude backward against the trajectory
    if length(x) > sensor_lag_samples
        x = x(1 : end - sensor_lag_samples);
        y = y(1 : end - sensor_lag_samples);
        mag = mag(sensor_lag_samples + 1 : end);
    end
    
    F = scatteredInterpolant(x, y, mag, 'linear', 'none');
    V_layer = F(Xq, Yq);
    
    flight_mask = flight_mask & isnan(V_layer);
    V_layer(isnan(V_layer)) = median(mag); 
    
    dist_x = sum(abs(diff(x))); dist_y = sum(abs(diff(y)));
    
    if dist_x > dist_y
        % X-Sweep (Scanning for Vertical Bars)
        fprintf('File %d (X-Sweep): Extracting vertical ridges...\n', i);
        V_match = conv2(V_layer, triplet_template, 'same');
        V_match(V_match < 0) = 0; 
        
        % Pre-smooth to ensure jagged ridges become a single clear peak
        V_smooth = imgaussfilt(V_match, 1.0);
        
        % Robust Horizontal NMS (>= prevents flat-top annihilation)
        V_left = [V_smooth(:, 1), V_smooth(:, 1:end-1)];
        V_right = [V_smooth(:, 2:end), V_smooth(:, end)];
        is_max = (V_smooth >= V_left) & (V_smooth >= V_right) & (V_match > 0);
        
        V_match = V_match .* is_max;
        
    else
        % Y-Sweep (Scanning for Horizontal Bars)
        fprintf('File %d (Y-Sweep): Extracting horizontal ridges...\n', i);
        V_match = conv2(V_layer, triplet_template', 'same');
        V_match(V_match < 0) = 0; 
        
        % Pre-smooth to ensure jagged ridges become a single clear peak
        V_smooth = imgaussfilt(V_match, 1.0);
        
        % Robust Vertical NMS
        V_up = [V_smooth(1, :); V_smooth(1:end-1, :)];
        V_down = [V_smooth(2:end, :); V_smooth(end, :)];
        is_max = (V_smooth >= V_up) & (V_smooth >= V_down) & (V_match > 0);
        
        V_match = V_match .* is_max;
    end
    
    % Dilation widens the razor-thin 1-pixel crest to ~3 pixels (1.5cm) so it 
    % renders beautifully on screen, without decreasing the peak match score.
    V_match = imdilate(V_match, strel('square', 3));
    V_presence_stack(:,:,i) = imgaussfilt(V_match, 0.5);
end

%% 5. Merge and Format Presence Map
V_final_presence = max(V_presence_stack, [], 3);

% --- ROBUST NORMALIZATION ---
% Ignore single-pixel extreme glitches by using the 99.5th percentile for max.
% (Done manually with sort() to avoid requiring the Statistics Toolbox)
valid_vals = sort(V_final_presence(V_final_presence > 0.01));
if ~isempty(valid_vals)
    idx_99 = max(1, round(0.995 * length(valid_vals)));
    robust_max = valid_vals(idx_99);
    
    if robust_max < 1e-6
        robust_max = max(V_final_presence(:)); 
    end
    V_final_presence = (V_final_presence / robust_max) * 100;
end

V_final_presence(V_final_presence > 100) = 100; % Cap outlier glitches at 100%
V_final_presence(V_final_presence < 20) = 0;    % User's Threshold

V_final_presence(flight_mask) = NaN; 
V_final_presence(V_final_presence == 0) = NaN; 

%% 6. Render Binary-Style Map
figure('Name', 'Physical Triplet Presence Map', 'Position', [100, 100, 900, 750]);

pcolor(Xq, Yq, V_final_presence); 
shading interp; 
colormap(gca, turbo); 

cb = colorbar;
ylabel(cb, 'Shape Match Confidence (%)', 'FontSize', 12, 'FontWeight', 'bold');

title('Target Presence Map (Lag Corrected & Robust NMS)', 'FontSize', 14);
xlabel('X Position (cm)', 'FontSize', 12); 
ylabel('Y Position (cm)', 'FontSize', 12);

axis equal tight; 
grid on; 
set(gca, 'Color', [0.02 0.02 0.1], 'FontSize', 11);