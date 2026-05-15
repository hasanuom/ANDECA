% Eddy Current - Morphological Vector Extraction
% Flattens the 12mm slope so the 6mm bar can be detected, merges triplets, 
% and plots exact center-mass CAD dots.
clear; clc; close all;

%% 1. Configuration & Tunable Parameters
target_folder = 'heatmap4';
target_mag = 'magnitude_h2'; 

% --- TIME DELAY (ZIG-ZAG FIX) ---
% Your discovery: 17 samples flawlessly straightens the tracking delay.
sensor_lag_samples = 17; 

% --- AMPLITUDE CLASSIFICATION THRESHOLDS ---
% Evaluated on absolute raw data. Adjust if colors are swapped.
thresh_12mm = 400.0; % > 400 is 12mm (Red)
thresh_8mm  = 80.0;  % 80 to 400 is 8mm (Orange)
thresh_6mm  = 8.0;   % 8 to 80 is 6mm (Cyan)

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

%% 2. 1D Smart Vector Extraction
peaks_12mm = []; peaks_8mm = []; peaks_6mm = [];
all_path_x = []; all_path_y = [];

for i = 1:length(valid_files)
    T = readtable(valid_files{i});
    x = T.x_m * 100; y = T.y_m * 100; mag = T.(target_mag);
    
    % --- 1. LAG CORRECTION ---
    if length(x) > sensor_lag_samples
        x = x(1 : end - sensor_lag_samples);
        y = y(1 : end - sensor_lag_samples);
        mag = mag(sensor_lag_samples + 1 : end);
    end
    
    % Smooth out Vicon tracking jitter
    x = smoothdata(x, 'gaussian', 10);
    y = smoothdata(y, 'gaussian', 10);
    
    all_path_x = [all_path_x; x; NaN];
    all_path_y = [all_path_y; y; NaN];
    
    % --- 2. CONVERT TO 1D DISTANCE ---
    dx = [0; diff(x)]; dy = [0; diff(y)];
    ds = sqrt(dx.^2 + dy.^2);
    s = cumsum(ds);
    
    [s_unq, unq_idx] = unique(s, 'stable');
    if length(s_unq) < 20, continue; end
    
    % Resample to exactly 1mm (0.1cm) spatial increments
    s_reg = 0 : 0.1 : max(s_unq); 
    x_reg = interp1(s_unq, x(unq_idx), s_reg, 'linear');
    y_reg = interp1(s_unq, y(unq_idx), s_reg, 'linear');
    mag_reg = interp1(s_unq, mag(unq_idx), s_reg, 'linear');
    
    % --- 3. BASELINE FLATTENING (The 6mm Savior) ---
    % A 15cm rolling window traces the "floor" of the signal. 
    % Subtracting this floor removes the massive 12mm mountain slope,
    % placing the 6mm speedbump onto perfectly flat ground!
    bg_floor = movmin(mag_reg, 150); % 150 samples = 15cm
    bg_smooth = movmax(bg_floor, 150); 
    mag_flat = mag_reg - bg_smooth;
    mag_flat(mag_flat < 0) = 0;
    
    % --- 4. THE TRIPLET MELTER ---
    % An 8cm spatial blur physically melts the center peak and side peaks 
    % of the triplet/doublet into ONE massive, smooth mountain.
    mag_melted = smoothdata(mag_flat, 'gaussian', 80); 
    
    % --- 5. CENTERLINE EXTRACTION ---
    % Find the absolute highest point of the melted mountain.
    % MinSeparation = 100mm (10cm) guarantees only ONE dot per rebar.
    is_peak = islocalmax(mag_melted, 'MinSeparation', 100);
    
    % Filter out empty-space wandering noise (must be > 2.0 amplitude)
    valid_peaks = find(is_peak & (mag_melted > 2.0));
    
    % --- 6. CLASSIFY & STORE ---
    for k = 1:length(valid_peaks)
        idx = valid_peaks(k);
        px = x_reg(idx);
        py = y_reg(idx);
        
        % Look up the true, absolute amplitude from the RAW data
        % (We look within a 4cm radius of the center to find the true max spike)
        search_window = max(1, idx-40) : min(length(mag_reg), idx+40);
        true_amp = max(mag_reg(search_window));
        
        if true_amp >= thresh_12mm
            peaks_12mm = [peaks_12mm; px, py];
        elseif true_amp >= thresh_8mm
            peaks_8mm = [peaks_8mm; px, py];
        else
            peaks_6mm = [peaks_6mm; px, py];
        end
    end
end

%% 3. Render CAD-Style Vector Map
figure('Name', 'Top-Hat Vector Map', 'Position', [100, 100, 900, 750]);
hold on;

% 1. Plot the scan path as faint tracking lines
plot(all_path_x, all_path_y, 'Color', [0.15 0.15 0.25], 'LineWidth', 1.0, 'DisplayName', 'Scan Path');

% 2. Plot 12mm Rebars (Thick Red)
if ~isempty(peaks_12mm)
    scatter(peaks_12mm(:,1), peaks_12mm(:,2), 160, 'r', 'filled', ...
        'MarkerEdgeColor', 'w', 'LineWidth', 1.2, 'DisplayName', '12mm Rebar');
end

% 3. Plot 8mm Rebars (Medium Orange)
if ~isempty(peaks_8mm)
    scatter(peaks_8mm(:,1), peaks_8mm(:,2), 90, [1 0.5 0], 'filled', ...
        'MarkerEdgeColor', 'w', 'LineWidth', 1.0, 'DisplayName', '8mm Rebar');
end

% 4. Plot 6mm Rebars (Thin Cyan)
if ~isempty(peaks_6mm)
    scatter(peaks_6mm(:,1), peaks_6mm(:,2), 45, 'c', 'filled', ...
        'MarkerEdgeColor', 'k', 'LineWidth', 0.8, 'DisplayName', '6mm Rebar');
end

hold off;

title('Target Presence Map (Top-Hat Baseline & Vector Extraction)', 'FontSize', 14);
xlabel('X Position (cm)', 'FontSize', 12); 
ylabel('Y Position (cm)', 'FontSize', 12);
legend('Location', 'northeastoutside', 'FontSize', 11);
axis equal tight; 
grid on; 
set(gca, 'Color', [0.05 0.05 0.1], 'GridColor', [0.3 0.3 0.4], 'FontSize', 11);