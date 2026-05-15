% Eddy Current Multi-Run Analysis & Averaging
clear; clc; close all;

%% Configuration Parameters
num_harmonics = 4;
num_bars = 3; % We expect 3 objects (12mm, 8mm, 6mm)

% --- Tweak these if it's not finding the 3 peaks correctly ---
% Minimum samples between actual bars. Looking at your plot, bars are ~300 samples apart.
% Setting this to 150 ensures we don't double-count jagged peaks on the SAME bar.
min_distance = 150; 
% Minimum height of a peak relative to the maximum signal in that run (e.g., 0.1 = 10%)
min_prominence_ratio = 0.10; 

%% Find all Run folders
% Find all directories that start with 'run'
items = dir('run*');
folder_names = {items([items.isdir]).name};
num_runs = length(folder_names);

if num_runs == 0
    error('No folders starting with "run" were found in the current directory.');
end
fprintf('Found %d runs to analyze.\n', num_runs);

%% Data Storage
% Store peak magnitudes: Dimensions = (Runs x Harmonics x Bars)
peak_data = NaN(num_runs, num_harmonics, num_bars);

% For averaging signals, we need a common X-axis because hand speeds vary
common_x = -500:2000; % Define an aligned sample index range
aligned_signals = NaN(num_runs, num_harmonics, length(common_x));

%% Figure 1 Setup (All Raw Runs Overlaid)
fig_raw = figure('Name', 'Raw Runs Overlaid', 'Position', [50, 50, 1000, 800]);

%% Process Each Run and Harmonic
for r = 1:num_runs
    current_folder = folder_names{r};
    
    for h = 0:(num_harmonics-1)
        filename = fullfile(current_folder, sprintf('harmonics_%d.csv', h));
        
        if ~isfile(filename)
            warning('File %s not found. Skipping.', filename);
            continue;
        end
        
        % Read data
        T = readtable(filename);
        raw_index = T{:, 2}; 
        magnitude = T{:, 5};
        
        % --- Robust Peak Detection ---
        % Calculate a dynamic noise floor based on the maximum signal in this specific file
        dynamic_min_height = max(magnitude) * min_prominence_ratio;
        
        % Find peaks: We do NOT sort by descend here. We let it find them chronologically.
        [pks, locs] = findpeaks(magnitude, ...
            'MinPeakDistance', min_distance, ...
            'MinPeakHeight', dynamic_min_height);
        
        % Extract the first 3 chronological peaks
        if length(pks) >= num_bars
            bar_pks = pks(1:num_bars);
            bar_locs = locs(1:num_bars);
            
            % Store the peak values for final analysis
            peak_data(r, h+1, :) = bar_pks;
            
            % --- Time Alignment for Averaging ---
            % Shift the x-axis so the FIRST peak is exactly at x=0
            shift_amount = raw_index(bar_locs(1));
            shifted_index = raw_index - shift_amount;
            
            % Interpolate this run's data onto the common x-axis
            % Remove duplicate indices if any exist due to sensor logging glitches
            [unique_idx, unq_i] = unique(shifted_index);
            aligned_signals(r, h+1, :) = interp1(unique_idx, magnitude(unq_i), common_x, 'linear', NaN);
            
        else
            fprintf('  Warning: Run %d, Harmonic %d only found %d peaks. Check min_distance.\n', r, h, length(pks));
        end
        
        % --- Plot Raw Data on Figure 1 ---
        figure(fig_raw);
        subplot(num_harmonics, 1, h+1);
        hold on;
        plot(raw_index, magnitude, 'LineWidth', 1, 'DisplayName', current_folder);
        if length(pks) >= num_bars
             plot(raw_index(bar_locs), bar_pks, 'k*', 'MarkerSize', 5, 'HandleVisibility','off');
        end
        title(sprintf('Harmonic %d - Raw Data', h));
        ylabel('Magnitude');
        if r == num_runs % Add legend on last pass
            legend('Location', 'best');
        end
    end
end
xlabel('Sample Index');

%% Figure 2 Setup (Average Signal with Shading)
fig_avg = figure('Name', 'Average Signals (+/- 10%)', 'Position', [1080, 50, 800, 800]);

for h = 0:(num_harmonics-1)
    figure(fig_avg);
    subplot(num_harmonics, 1, h+1);
    hold on;
    
    % Extract all aligned signals for this harmonic across all runs
    % squeeze removes the harmonic dimension, leaving a matrix of (Runs x Common_X)
    data_matrix = squeeze(aligned_signals(:, h+1, :)); 
    
    % Calculate Mean
    avg_signal = nanmean(data_matrix, 1);
    
    % Calculate +/- 10% Bounds based on your request
    upper_bound = avg_signal * 1.10;
    lower_bound = avg_signal * 0.90;
    
    % Filter out NaNs for the shading to work properly
    valid_idx = ~isnan(avg_signal);
    x_valid = common_x(valid_idx);
    upper_valid = upper_bound(valid_idx);
    lower_valid = lower_bound(valid_idx);
    
    % Plot Shaded Area
    % Create polygon coordinates: [x_forward, x_backward], [upper_forward, lower_backward]
    fill([x_valid, fliplr(x_valid)], [upper_valid, fliplr(lower_valid)], ...
        [0.8 0.8 1], 'EdgeColor', 'none', 'FaceAlpha', 0.5, 'DisplayName', '+/- 10% Area');
    
    % Plot Average Line
    plot(x_valid, avg_signal(valid_idx), 'b-', 'LineWidth', 2, 'DisplayName', 'Average Signal');
    
    title(sprintf('Harmonic %d - Aligned Average', h));
    ylabel('Magnitude');
    grid on;
    if h == 0
        legend('Location', 'best');
    end
    
    % Set axis limits to zoom in on the actual data
    xlim([-200, 1500]); 
end
xlabel('Aligned Sample Index (0 = First Peak)');


%% Final Analysis & Conclusion based on Averages
fprintf('\n=======================================\n');
fprintf('FINAL AVERAGED RESULTS ACROSS %d RUNS\n', num_runs);
fprintf('=======================================\n');

for h = 0:(num_harmonics-1)
    fprintf('\n--- Harmonic %d ---\n', h);
    
    % Calculate the average peak magnitude for each bar across all runs
    avg_peaks = squeeze(nanmean(peak_data(:, h+1, :), 1));
    
    if any(isnan(avg_peaks))
         fprintf('Insufficient data to average peaks for this harmonic.\n');
         continue;
    end
    
    fprintf('1st object (12mm bar) Average Peak: %.2f\n', avg_peaks(1));
    fprintf('2nd object (8mm bar)  Average Peak: %.2f\n', avg_peaks(2));
    fprintf('3rd object (6mm bar)  Average Peak: %.2f\n', avg_peaks(3));
    
    % Logic check
    if (avg_peaks(1) > avg_peaks(2)) && (avg_peaks(2) > avg_peaks(3))
        fprintf('>>> SUCCESS: Sensor consistently differentiates sizes. (12mm > 8mm > 6mm)\n');
    elseif (avg_peaks(1) ~= avg_peaks(2)) && (avg_peaks(2) ~= avg_peaks(3)) && (avg_peaks(1) ~= avg_peaks(3))
        fprintf('>>> PARTIAL: Sensor sees different values, but doesn''t scale perfectly with size.\n');
    else
        fprintf('>>> FAIL: Sensor cannot clearly differentiate sizes on average.\n');
    end
end
fprintf('=======================================\n');