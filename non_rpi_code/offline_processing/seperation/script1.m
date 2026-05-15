% Eddy Current - Multi-Pass Spatial Resolution (Peak Counting Method)
clear; clc; close all;

%% Configuration Parameters
focus_h = 1; 

% --- Signal Processing Parameters ---
smooth_window = 15;           
baseline_window = 500; 

% Stage 1: Macro-Detection
tracker_window = 100; 
min_sweep_distance = 150; 
local_search_radius = 120; 

%% Find all distance folders
items = dir('*mm*'); 
folder_names = {items([items.isdir]).name};
num_folders = length(folder_names);

if num_folders == 0
    error('No folders containing "mm" were found.');
end

%% Plotting Setup
figure('Name', 'Spatial Resolution Progression (Harmonic 1)', 'Position', [50, 50, 1600, 1000]);

fprintf('\n=======================================================\n');
fprintf('MULTI-PASS SPATIAL RESOLUTION ANALYSIS (PEAK COUNTING)\n');
fprintf('=======================================================\n');

%% Process Data
for f = 1:num_folders
    current_folder = folder_names{f};
    filename = fullfile(current_folder, sprintf('harmonics_%d.csv', focus_h));
    
    if ~isfile(filename), continue; end
    
    T = readtable(filename);
    magnitude = T{:, 5}; 
    
    % --- BASELINE DETRENDING ---
    baseline = smoothdata(magnitude, 'movmedian', baseline_window);
    mag_flat = magnitude - baseline;
    mag_clean = smoothdata(mag_flat, 'movmedian', smooth_window);
    
    % --- STAGE 1: GLITCH-PROOF MACRO DETECTION ---
    % Use absolute value, NOT squaring, to prevent glitches from exploding in size
    sweep_tracker = smoothdata(abs(mag_clean), 'movmean', tracker_window);
    
    % Calculate the 95th percentile instead of max() to completely ignore massive spikes
    sorted_tracker = sort(sweep_tracker);
    tracker_p95 = sorted_tracker(round(length(sorted_tracker) * 0.95));
    
    if tracker_p95 <= 0, continue; end
    
    min_sweep_height = tracker_p95 * 0.3; % Dynamic threshold based on healthy data
    
    [~, sweep_locs] = findpeaks(sweep_tracker, ...
        'MinPeakDistance', min_sweep_distance, ...
        'MinPeakHeight', min_sweep_height);
    
    % --- Plotting the Folder Run ---
    subplot(num_folders, 1, f);
    hold on;
    plot(mag_clean, 'Color', [0.6 0.8 1], 'LineWidth', 1, 'DisplayName', 'Detrended Signal');
    plot(sweep_tracker, 'Color', [0.8 0.8 0.8], 'LineStyle', '--', 'LineWidth', 1.5, 'DisplayName', 'Sweep Tracker');
    
    fprintf('\n--- %s ---\n', current_folder);
    
    valid_sweeps_count = 0;
    resolved_count = 0;
    
    % --- STAGE 2: ANALYZE INDIVIDUAL SWEEPS (PEAK COUNTING) ---
    % --- STAGE 2: ANALYZE INDIVIDUAL SWEEPS (PEAK COUNTING) ---
    for s = 1:length(sweep_locs)
        center = sweep_locs(s);
        search_range = max(1, center - local_search_radius) : min(length(mag_clean), center + local_search_radius);
        local_sig = mag_clean(search_range);
        
        local_max = max(local_sig);
        
        % SAFETY CHECK: Only search for peaks if the sweep is actually in positive territory
        if local_max > 0
            % Find all distinct prominent peaks in this specific sweep
            % Using the higher sensitivity settings (0.10 and 15) to catch slow peaks
            local_min_prom = local_max * 0.10; 
            [local_pks, local_locs] = findpeaks(local_sig, 'MinPeakProminence', local_min_prom, 'MinPeakDistance', 10);
        else
            local_pks = [];
            local_locs = [];
        end
        
        global_locs = search_range(1) + local_locs - 1;
        num_peaks = length(local_pks);
        
        if num_peaks >= 3
            % RESOLVED: M-M shape detected
            plot(global_locs, local_pks, 'g^', 'MarkerFaceColor', 'g', 'MarkerSize', 8, 'HandleVisibility', 'off');
            valid_sweeps_count = valid_sweeps_count + 1;
            resolved_count = resolved_count + 1;
        elseif num_peaks == 2 || num_peaks == 1
            % MERGED: Single M shape detected (or totally fused single peak)
            plot(global_locs, local_pks, 'rx', 'MarkerSize', 10, 'LineWidth', 2, 'HandleVisibility', 'off');
            valid_sweeps_count = valid_sweeps_count + 1;
        else
            % GLITCH: 0 peaks, negative signal, or messy noise.
            plot(center, max(local_sig), 'kx', 'MarkerSize', 8, 'HandleVisibility', 'off');
        end
    end
    
    % --- Summarize Folder Results ---
    if valid_sweeps_count > 0
        resolve_rate = (resolved_count / valid_sweeps_count) * 100;
        fprintf('Analyzed %d valid sweeps.\n', valid_sweeps_count);
        
        if resolve_rate > 50
            fprintf('>> STATUS: RESOLVED (%d%% of passes successful)\n', round(resolve_rate));
            title(sprintf('%s | RESOLVED (%d%%)', current_folder, round(resolve_rate)));
        else
            fprintf('>> STATUS: MERGED (Failed to resolve %d%% of passes)\n', round(100 - resolve_rate));
            title(sprintf('%s | MERGED', current_folder));
        end
    else
        title(sprintf('%s | NO VALID DATA', current_folder));
        fprintf('No valid dual-peak sweeps found.\n');
    end
    
    grid on; ylabel('Magnitude');
    if f == 1, legend('Location', 'northeast'); end
    if f == num_folders, xlabel('Packet #'); end
end
fprintf('=======================================================\n');