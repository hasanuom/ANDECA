% Eddy Current - Individual Bar Extraction and Averaging
clear; clc; close all;

%% Configuration Parameters
num_harmonics = 4;
bar_names = {'12mm Bar', '8mm Bar', '6mm Bar'};
num_bars = length(bar_names);

% --- Signal Processing Parameters ---
% 1. Ignore early noise: Samples before this index are set to 0 before searching for peaks
ignore_initial_samples = 200; 

% 2. Minimum distance between actual bars (prevents double-counting a jagged peak)
min_distance = 150; 

% 3. Window size: How many samples to extract before and after the peak to draw the shape.
% Looking at your graphs, a peak is about 100 samples wide. +/- 70 frames it perfectly.
window_half_width = 70; 
window_axis = -window_half_width : window_half_width; 

%% Find all Run folders
items = dir('run*');
folder_names = {items([items.isdir]).name};
num_runs = length(folder_names);

if num_runs == 0
    error('No folders starting with "run" were found in the current directory.');
end
fprintf('Found %d runs to analyze.\n', num_runs);

%% Data Storage Pre-allocation
% Matrix shape: (Runs x Harmonics x Bars x Window_Length)
aligned_snippets = NaN(num_runs, num_harmonics, num_bars, length(window_axis));
peak_magnitudes = NaN(num_runs, num_harmonics, num_bars);

%% Process Data and Extract Snippets
for r = 1:num_runs
    current_folder = folder_names{r};
    
    for h = 0:(num_harmonics-1)
        filename = fullfile(current_folder, sprintf('harmonics_%d.csv', h));
        if ~isfile(filename), continue; end
        
        T = readtable(filename);
        magnitude = T{:, 5};
        
        % Filter out the early noise
        mag_clean = magnitude;
        mag_clean(1:min(ignore_initial_samples, length(mag_clean))) = 0;
        
        % Dynamic minimum height (must be at least 15% of the max signal)
        min_height = max(mag_clean) * 0.15;
        
        % Find peaks chronologically
        [pks, locs] = findpeaks(mag_clean, ...
            'MinPeakDistance', min_distance, ...
            'MinPeakHeight', min_height);
        
        % If we found at least 3 peaks, extract them
        if length(pks) >= num_bars
            for b = 1:num_bars
                center_idx = locs(b);
                peak_magnitudes(r, h+1, b) = pks(b);
                
                % Extract the window around the peak
                for w_idx = 1:length(window_axis)
                    offset = window_axis(w_idx);
                    target_idx = center_idx + offset;
                    
                    % Ensure we don't try to read outside the array bounds
                    if target_idx > 0 && target_idx <= length(magnitude)
                        aligned_snippets(r, h+1, b, w_idx) = magnitude(target_idx);
                    end
                end
            end
        else
            fprintf('Warning: Run %d, Harmonic %d only found %d valid peaks.\n', r, h, length(pks));
        end
    end
end

%% Plotting - 4x3 Grid (Harmonics vs Bars)
figure('Name', 'Isolated Bar Comparison (Aligned Peaks)', 'Position', [50, 50, 1600, 1000]);

% Color palette for individual runs
colors = lines(num_runs); 

for h = 1:num_harmonics
    for b = 1:num_bars
        % Calculate subplot index (1 to 12)
        subplot_idx = (h-1)*num_bars + b;
        subplot(num_harmonics, num_bars, subplot_idx);
        hold on;
        
        % Extract the snippet data for this specific harmonic and bar
        % squeeze() turns the 4D matrix into a 2D matrix of (Runs x Window_Length)
        plot_data = squeeze(aligned_snippets(:, h, b, :)); 
        
        % 1. Calculate Average and +/- 10% bounds
        avg_line = nanmean(plot_data, 1);
        upper_bound = avg_line * 1.10;
        lower_bound = avg_line * 0.90;
        
        % 2. Draw the +/- 10% Shaded Area
        fill([window_axis, fliplr(window_axis)], [upper_bound, fliplr(lower_bound)], ...
            [0.85 0.85 1], 'EdgeColor', 'none', 'FaceAlpha', 0.6, 'DisplayName', '+/- 10% Area');
        
        % 3. Plot individual runs (Thin lines)
        for r = 1:num_runs
            plot(window_axis, plot_data(r, :), 'Color', [colors(r,:) 0.5], ...
                'LineWidth', 1, 'DisplayName', folder_names{r});
        end
        
        % 4. Plot the Average Line (Thick Blue line)
        plot(window_axis, avg_line, 'b-', 'LineWidth', 2.5, 'DisplayName', 'Average');
        
        % Formatting
        title(sprintf('Harmonic %d: %s', h-1, bar_names{b}));
        grid on;
        xlim([-window_half_width, window_half_width]);
        
        % Only add legend to the very first subplot so it doesn't clutter everything
        if subplot_idx == 1
            legend('Location', 'northeast', 'FontSize', 8);
        end
        
        if h == num_harmonics
            xlabel('Samples from Peak');
        end
        if b == 1
            ylabel('Magnitude');
        end
    end
end

%% Console Output Analysis
fprintf('\n=======================================\n');
fprintf('FINAL AVERAGED PEAK MAGNITUDES\n');
fprintf('=======================================\n');

for h = 1:num_harmonics
    fprintf('\n--- Harmonic %d ---\n', h-1);
    
    avg_pks = nanmean(peak_magnitudes(:, h, :), 1);
    avg_pks = squeeze(avg_pks); % Clean up array dimensions
    
    if any(isnan(avg_pks))
        fprintf('  Missing data, cannot compute.\n');
        continue;
    end
    
    fprintf('  12mm Bar: %.1f\n', avg_pks(1));
    fprintf('   8mm Bar: %.1f\n', avg_pks(2));
    fprintf('   6mm Bar: %.1f\n', avg_pks(3));
    
    % Differentiation check
    if (avg_pks(1) > avg_pks(2)) && (avg_pks(2) > avg_pks(3))
        fprintf('  >>> SUCCESS: Scales perfectly by size.\n');
    else
        fprintf('  >>> PARTIAL/FAIL: Does not scale perfectly linearly by size.\n');
    end
end
fprintf('=======================================\n');