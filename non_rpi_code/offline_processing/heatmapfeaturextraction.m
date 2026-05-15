% Eddy Current - Local-Window Peak Clustering (The 6mm Savior)
% Uses the exact empirical logic that successfully found the 6mm footprint.
clear; clc; close all;

%% 1. Configuration & Tunable Parameters
target_folder = 'heatmap4';
target_mag = 'magnitude_h2'; 

% --- THE GOLDEN FIX ---
sensor_lag_samples = 17; % Perfectly aligns your Vicon data

% --- EMPIRICAL AMPLITUDE THRESHOLDS ---
thresh_12mm = 600.0; % > 600 is 12mm (Thick Red)
thresh_8mm  = 80.0;  % 80 to 600 is 8mm (Medium Orange)
thresh_6mm  = 10.0;  % 10 to 80 is 6mm (Thin Cyan)

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

%% 2. 1D Vector Peak Extraction & Clustering
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
    
    % --- 2. DIRECTIONAL FILTERING ---
    % Skip vertical transit paths to prevent false orthogonal hits
    dist_x = sum(abs(diff(x))); dist_y = sum(abs(diff(y)));
    if dist_y > dist_x
        continue; 
    end
    
    % --- 3. CONVERT TO 1D DISTANCE ---
    dx = [0; diff(x)]; dy = [0; diff(y)];
    ds = sqrt(dx.^2 + dy.^2);
    s = cumsum(ds);
    
    [s_unq, unq_idx] = unique(s, 'stable');
    if length(s_unq) < 50, continue; end
    
    % Resample to exactly 1mm (0.1cm) spatial increments
    s_reg = 0 : 0.1 : max(s_unq); 
    x_reg = interp1(s_unq, x(unq_idx), s_reg, 'linear');
    y_reg = interp1(s_unq, y(unq_idx), s_reg, 'linear');
    mag_reg = interp1(s_unq, mag(unq_idx), s_reg, 'linear');
    
    % --- 4. EXACT EMPIRICAL PEAK FINDING ---
    % 1.5cm blur just to kill static. Preserves the tiny 6mm peak!
    mag_smooth = smoothdata(mag_reg, 'gaussian', 15); 
    
    [pks, locs] = findpeaks(mag_smooth, ...
        'MinPeakHeight', 8.0, ...       % Low enough to catch 6mm
        'MinPeakProminence', 3.0, ...   % Prominence ignores background drift
        'MinPeakDistance', 80);         % 8cm minimum separation
    
    if isempty(locs)
        continue;
    end
    
    % --- 5. CLUSTER THE PEAKS ---
    % Because the 12mm bar has side-peaks 10cm away, we group any peaks
    % that are within 12cm of each other to find the TRUE single center.
    group_locs = locs(1);
    
    for k = 2:length(locs)
        if (locs(k) - group_locs(end)) <= 120 % 12cm grouping window
            group_locs(end+1) = locs(k);
        else
            % We finished a group (a single rebar). Process it:
            [~, max_idx] = max(mag_smooth(group_locs));
            center_loc = group_locs(max_idx);
            
            % EXACT EMPIRICAL LOCAL BASELINE CALCULATION
            snip_start = max(1, center_loc - 150);
            snip_end   = min(length(mag_reg), center_loc + 150);
            true_amp   = mag_reg(center_loc) - min(mag_reg(snip_start:snip_end));
            
            px = x_reg(center_loc);
            py = y_reg(center_loc);
            
            % Classify and Store
            if true_amp >= thresh_12mm
                peaks_12mm = [peaks_12mm; px, py];
            elseif true_amp >= thresh_8mm
                peaks_8mm = [peaks_8mm; px, py];
            else
                peaks_6mm = [peaks_6mm; px, py];
            end
            
            % Start the next group
            group_locs = locs(k);
        end
    end
    
    % Process the final group in the sweep
    [~, max_idx] = max(mag_smooth(group_locs));
    center_loc = group_locs(max_idx);
    
    snip_start = max(1, center_loc - 150);
    snip_end   = min(length(mag_reg), center_loc + 150);
    true_amp   = mag_reg(center_loc) - min(mag_reg(snip_start:snip_end));
    
    px = x_reg(center_loc);
    py = y_reg(center_loc);
    
    if true_amp >= thresh_12mm
        peaks_12mm = [peaks_12mm; px, py];
    elseif true_amp >= thresh_8mm
        peaks_8mm = [peaks_8mm; px, py];
    else
        peaks_6mm = [peaks_6mm; px, py];
    end
end

%% 3. Render CAD-Style Vector Map
figure('Name', 'Clustered Empirical Vector Map', 'Position', [100, 100, 900, 750]);
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

title('Target Presence Map (Local-Window Clustering & Classification)', 'FontSize', 14);
xlabel('X Position (cm)', 'FontSize', 12); 
ylabel('Y Position (cm)', 'FontSize', 12);
legend('Location', 'northeastoutside', 'FontSize', 11);
axis equal tight; 
grid on; 
set(gca, 'Color', [0.05 0.05 0.1], 'GridColor', [0.3 0.3 0.4], 'FontSize', 11);