% =========================================================================
% EDDY CURRENT NDT: Subsurface Tomography & Target Occupancy Pipeline
% Final Master Script - Integrates Hysteresis Correction, 1D Spatial
% Triplet Detection, Non-Maximum Suppression (NMS), and Robust Normalization
% =========================================================================
clear; clc; close all;

%% 1. System Configuration & Tuning Parameters
target_folder = 'heatmap2';     % Target directory containing Vicon CSVs
target_mag    = 'magnitude_h2'; % Target harmonic column

% --- HARDWARE TUNING ---
% Latency compensation: Shifts magnetic data backward in time to align 
% with Vicon spatial coordinates, fixing the bidirectional "zig-zag" offset.
sensor_lag_samples = 7; 

% --- ALGORITHM TUNING ---
grid_res = 0.5;         % Virtual spatial grid resolution (cm)
presence_thresh = 20;   % Minimum confidence (%) to render on final map

if ~isfolder(target_folder)
    error('Folder "%s" not found. Run from parent directory.', target_folder);
end

% Load valid files (ignoring redundant harmonic suffixes)
files = dir(fullfile(target_folder, '*.csv'));
valid_files = {};
for i = 1:length(files)
    if contains(files(i).name, '_h0') || contains(files(i).name, '_h1') || ...
       contains(files(i).name, '_h2') || contains(files(i).name, '_h3')
        continue; 
    end
    valid_files{end+1} = fullfile(target_folder, files(i).name);
end

%% 2. Global Boundaries & Spatial Grid Initialization
all_x = []; all_y = [];
for i = 1:length(valid_files)
    T = readtable(valid_files{i});
    all_x = [all_x; T.x_m * 100]; all_y = [all_y; T.y_m * 100];
end

% --- NEW: SHIFT COORDINATES TO PREVENT NEGATIVE AXES ---
% Finds the minimum Y (and X) and shifts all data so the scan starts at 0.
% This preserves all data without artificially cropping the plots.
offset_y = min(all_y);
if offset_y < 0
    all_y = all_y - offset_y;
else
    offset_y = 0; % No shift needed if already strictly positive
end

offset_x = min(all_x);
if offset_x < 0
    all_x = all_x - offset_x;
else
    offset_x = 0;
end
% -------------------------------------------------------

[Xq, Yq] = meshgrid(floor(min(all_x)):grid_res:ceil(max(all_x)), ...
                    floor(min(all_y)):grid_res:ceil(max(all_y)));

%% 3. Physical Template Synthesis (The 12cm D-Coil Triplet)
% Models the exact physical footprint of a perpendicular rebar crossing
x_k = -8 : grid_res : 8; 
triplet_template = exp(-(x_k).^2 / 2) + ...
                   0.5 * exp(-(x_k - 4.0).^2 / 2) + ...
                   0.5 * exp(-(x_k + 4.0).^2 / 2);
               
% Zero-mean forces it to act as a pure shape-matching filter
triplet_template = triplet_template - mean(triplet_template);

%% 4. Main Processing Pipeline (Interpolation, NMS, & Dilation)
V_raw_stack = zeros(size(Xq, 1), size(Xq, 2), length(valid_files));
V_presence_stack = zeros(size(Xq, 1), size(Xq, 2), length(valid_files));
flight_mask = true(size(Xq)); 

diag_stored = false;
diag_data = struct();
max_global_hit = 0;

for i = 1:length(valid_files)
    T = readtable(valid_files{i});
    x = T.x_m * 100; y = T.y_m * 100; mag = T.(target_mag);
    
    % --- Apply Spatial Offsets to match the shifted grid ---
    x = x - offset_x;
    y = y - offset_y;
    
    % --- 4a. Hysteresis / Latency Correction ---
    if length(x) > sensor_lag_samples
        x = x(1 : end - sensor_lag_samples);
        y = y(1 : end - sensor_lag_samples);
        mag = mag(sensor_lag_samples + 1 : end);
    end
    
    % --- 4b. Spatial Interpolation ---
    F = scatteredInterpolant(x, y, mag, 'linear', 'none');
    V_layer = F(Xq, Yq);
    
    flight_mask = flight_mask & isnan(V_layer);
    
    % Store purely raw (but aligned) data for Map 1
    V_raw_stack(:,:,i) = V_layer;
    
    % Neutralize un-flown areas to prevent edge-ringing during convolution
    V_layer(isnan(V_layer)) = median(mag); 
    
    % --- 4c. Directional Convolution & NMS ---
    dist_x = sum(abs(diff(x))); dist_y = sum(abs(diff(y)));
    
    if dist_x > dist_y
        % X-Sweep (Extracting Vertical Bars)
        fprintf('Phase %d (X-Sweep): Extracting vertical ridges...\n', i);
        V_match = conv2(V_layer, triplet_template, 'same');
        V_match(V_match < 0) = 0; % Rectify to kill parallel "M-Shape" noise
        
        V_smooth = imgaussfilt(V_match, 1.0); % Pre-smooth for NMS
        
        % Robust Horizontal Non-Maximum Suppression (NMS)
        V_left = [V_smooth(:, 1), V_smooth(:, 1:end-1)];
        V_right = [V_smooth(:, 2:end), V_smooth(:, end)];
        is_max = (V_smooth >= V_left) & (V_smooth >= V_right) & (V_match > 0);
        V_match = V_match .* is_max;
        
    else
        % Y-Sweep (Extracting Horizontal Bars)
        fprintf('Phase %d (Y-Sweep): Extracting horizontal ridges...\n', i);
        V_match = conv2(V_layer, triplet_template', 'same');
        V_match(V_match < 0) = 0; 
        
        V_smooth = imgaussfilt(V_match, 1.0);
        
        % Robust Vertical Non-Maximum Suppression (NMS)
        V_up = [V_smooth(1, :); V_smooth(1:end-1, :)];
        V_down = [V_smooth(2:end, :); V_smooth(end, :)];
        is_max = (V_smooth >= V_up) & (V_smooth >= V_down) & (V_match > 0);
        V_match = V_match .* is_max;
    end
    
    % --- 4d. Morphological Dilation ---
    % Widens the razor-thin 1-pixel NMS crest to ~1.5cm for rendering visibility
    V_match = imdilate(V_match, strel('square', 3));
    V_smoothed_final = imgaussfilt(V_match, 0.5);
    V_presence_stack(:,:,i) = V_smoothed_final;
    
    % --- 4e. Diagnostic Data Capture ---
    % Automatically hunts for the strongest signal hit to generate the 1D proof
    current_max = max(V_smoothed_final(:));
    if current_max > max_global_hit
        max_global_hit = current_max;
        [r, c] = ind2sub(size(V_smoothed_final), find(V_smoothed_final == current_max, 1));
        
        if dist_x > dist_y
            diag_data.pos  = Xq(r, :);
            diag_data.raw  = V_layer(r, :);
            diag_data.conv = conv2(V_layer, triplet_template, 'same');
            diag_data.sm   = V_smoothed_final(r, :);
            diag_data.type = sprintf('X-Sweep (Horizontal Slice at Y = %.1f cm)', Yq(r,1));
        else
            diag_data.pos  = Yq(:, c)';
            diag_data.raw  = V_layer(:, c)';
            diag_data.conv = conv2(V_layer, triplet_template', 'same');
            diag_data.sm   = V_smoothed_final(:, c)';
            diag_data.type = sprintf('Y-Sweep (Vertical Slice at X = %.1f cm)', Xq(1,c));
        end
        diag_stored = true;
    end
end

%% 5. Merge & Robust Normalization
% --- MAP 1: Raw Magnitude Merge ---
V_final_raw = max(V_raw_stack, [], 3);
V_final_raw(flight_mask) = NaN; 

% --- MAP 2: Processed Presence Merge ---
V_final_presence = max(V_presence_stack, [], 3);

% Robust 99.5th Percentile AGC (Automatic Gain Control)
% Protects against artificial depression of valid signals due to random hardware spikes
valid_vals = sort(V_final_presence(V_final_presence > 0.01));
if ~isempty(valid_vals)
    idx_99 = max(1, round(0.995 * length(valid_vals)));
    robust_max = valid_vals(idx_99);
    if robust_max < 1e-6
        robust_max = max(V_final_presence(:)); 
    end
    V_final_presence = (V_final_presence / robust_max) * 100;
end

V_final_presence(V_final_presence > 100) = 100; % Cap extreme glitches
V_final_presence(V_final_presence < presence_thresh) = 0; % Thresholding
V_final_presence(flight_mask) = NaN; 
V_final_presence(V_final_presence == 0) = NaN; 

%% 6. Render Map 1: Raw Sensor Data (Aligned)
figure('Name', 'RAW SENSOR DATA (Aligned)', 'Position', [50, 100, 750, 650]);
pcolor(Xq, Yq, V_final_raw); 
shading flat; % Quantized occupancy grid style
colormap(gca, turbo);

cb1 = colorbar;
ylabel(cb1, 'Raw Magnetic Magnitude', 'FontSize', 12, 'FontWeight', 'bold');
title('Raw Sensor Output (Latency Aligned)', 'FontSize', 14);
xlabel('X Position (cm)', 'FontSize', 12); 
ylabel('Y Position (cm)', 'FontSize', 12);
% Find the maximum physical dimension to make a square bounding box
max_bound = max(max(Xq(:)), max(Yq(:)));
xlim([0, max_bound]);
ylim([0, max_bound]);
axis equal; % Keeps proportions physically accurate
grid on; set(gca, 'Color', [0.02 0.02 0.1], 'FontSize', 11);

%% 7. Render Map 2: Processed Target Occupancy
figure('Name', 'PROCESSED TARGET OCCUPANCY', 'Position', [820, 100, 750, 650]);
pcolor(Xq, Yq, V_final_presence); 
shading flat; % Quantized occupancy grid style
colormap(gca, turbo);

cb2 = colorbar;
ylabel(cb2, 'Shape Match Confidence (%)', 'FontSize', 12, 'FontWeight', 'bold');
title('Target Occupancy Grid (NMS Shape Detector)', 'FontSize', 14);
xlabel('X Position (cm)', 'FontSize', 12); 
ylabel('Y Position (cm)', 'FontSize', 12);
% Find the maximum physical dimension to make a square bounding box
max_bound = max(max(Xq(:)), max(Yq(:)));
xlim([0, max_bound]);
ylim([0, max_bound]);
axis equal; % Keeps proportions physically accurate
grid on; set(gca, 'Color', [0.02 0.02 0.1], 'FontSize', 11);

%% 8. Render Map 3: 1D Diagnostic Proof
if diag_stored
    figure('Name', 'DIAGNOSTIC — Computer Vision Pipeline Proof', 'Position', [400, 150, 1000, 800], 'Color', [0.04 0.04 0.10]);
    bg = [0.04 0.04 0.10];  fg = [0.85 0.90 1.00];
    
    ax1 = subplot(4,1,1);
    plot(diag_data.pos, diag_data.raw, 'Color', [0.4 0.7 1.0], 'LineWidth', 1.5);
    title(sprintf('① Raw Interpolated Signal Slice — %s', diag_data.type), 'Color', fg);
    ylabel('Magnitude', 'Color', fg);
    set(ax1, 'Color', bg, 'XColor', fg, 'YColor', fg, 'GridColor', [.3 .3 .4]); grid on;
    
    ax2 = subplot(4,1,2);
    plot(x_k, triplet_template, 'Color', [1 0.6 0.1], 'LineWidth', 2);
    yline(0, 'w--');
    title('② Physical D-Coil Template (Zero-Mean Triplet)', 'Color', fg);
    ylabel('Amplitude', 'Color', fg); xlabel('Offset (cm)', 'Color', fg);
    set(ax2, 'Color', bg, 'XColor', fg, 'YColor', fg, 'GridColor', [.3 .3 .4]); grid on;
    
    ax3 = subplot(4,1,3);
    plot(diag_data.pos, diag_data.conv, 'Color', [0.8 0.5 1.0], 'LineWidth', 1.5);
    yline(0, 'w--', 'LineWidth', 1.5);
    title('③ Spatial Convolution (Shape Match Score before rectification)', 'Color', fg);
    ylabel('Match Score', 'Color', fg);
    set(ax3, 'Color', bg, 'XColor', fg, 'YColor', fg, 'GridColor', [.3 .3 .4]); grid on;
    
    ax4 = subplot(4,1,4);
    plot(diag_data.pos, diag_data.sm, 'Color', [1 0.3 0.3], 'LineWidth', 2);
    yline(0, 'w--');
    title('④ Final NMS Centerline Extraction (Dilated & Normalized)', 'Color', fg);
    xlabel('Position (cm)', 'Color', fg); ylabel('Confidence Score (%)', 'Color', fg);
    set(ax4, 'Color', bg, 'XColor', fg, 'YColor', fg, 'GridColor', [.3 .3 .4]); grid on;
    
    % Link X-axes for aligned positional comparison
    linkaxes([ax1 ax3 ax4], 'x');
end