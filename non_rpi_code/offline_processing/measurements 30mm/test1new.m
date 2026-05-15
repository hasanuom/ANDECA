% Eddy Current - Gradiometer Doublet Extraction & Phase Invariance Analysis
clear; clc; close all;

%% Configuration Parameters
num_harmonics = 4;
bar_names = {'12mm Bar', '8mm Bar', '6mm Bar'};
num_bars = length(bar_names);

% --- Signal Processing Parameters ---
ignore_initial_samples = 200; 
smooth_window = 15;           
envelope_window = 50;         % Slightly increased to better bridge the 6mm bar gap
min_distance = 200;           
window_half_width = 120;      % Captures the full 'M' doublet
window_axis = -window_half_width : window_half_width;

%% Find all Run folders
items = dir('run*');
folder_names = {items([items.isdir]).name};
num_runs = length(folder_names);

if num_runs == 0
    error('No folders starting with "run" were found.');
end

%% Data Storage Pre-allocation
aligned_snippets = NaN(num_runs, num_harmonics, num_bars, length(window_axis));
peak_magnitudes  = NaN(num_runs, num_harmonics, num_bars);
peak_areas       = NaN(num_runs, num_harmonics, num_bars);
peak_phases      = NaN(num_runs, num_harmonics, num_bars);

%% Process Data and Extract Features
for r = 1:num_runs
    current_folder = folder_names{r};
    
    for h = 0:(num_harmonics-1)
        filename = fullfile(current_folder, sprintf('harmonics_%d.csv', h));
        if ~isfile(filename), continue; end
        
        T = readtable(filename);
        
        real_comp = T{:, 3}; 
        imag_comp = T{:, 4}; 
        magnitude = T{:, 5}; 
        
        % Calculate Phase in degrees
        phase_deg = rad2deg(atan2(imag_comp, real_comp));
        
        % Clean Signal (Smooth first)
        mag_clean = smoothdata(magnitude, 'movmedian', smooth_window);
        
        % Calculate Envelope BEFORE muting early noise to prevent edge artifacts
        [mag_envelope, ~] = envelope(mag_clean, envelope_window, 'peak');
        
        % Mute early noise on the envelope
        mag_envelope(1:min(ignore_initial_samples, length(mag_envelope))) = 0; 
        
        % Dynamic minimum height with a fallback to prevent findpeaks failure
        max_env = max(mag_envelope);
        if max_env <= 0 || isnan(max_env)
            fprintf('Warning: Run %d, Harmonic %d has invalid data.\n', r, h);
            continue;
        end
        min_height = max_env * 0.15;
        
        % Find peaks on the ENVELOPE to locate the geometric center of the doublet
        [pks, locs] = findpeaks(mag_envelope, ...
            'MinPeakDistance', min_distance, ...
            'MinPeakHeight', min_height);
            
        if length(pks) >= num_bars
            for b = 1:num_bars
                center_idx = locs(b);
                
                peak_magnitudes(r, h+1, b) = pks(b);
                peak_phases(r, h+1, b)     = phase_deg(center_idx);
                
                % Extract snippet
                valid_snippet = [];
                for w_idx = 1:length(window_axis)
                    offset = window_axis(w_idx);
                    target_idx = center_idx + offset;
                    
                    if target_idx > 0 && target_idx <= length(magnitude)
                        % Extract the SMOOTHED raw signal (the 'M' shape), not the envelope
                        val = mag_clean(target_idx); 
                        aligned_snippets(r, h+1, b, w_idx) = val;
                        valid_snippet = [valid_snippet, val];
                    end
                end
                
                if ~isempty(valid_snippet)
                    peak_areas(r, h+1, b) = trapz(valid_snippet);
                end
            end
        else
            fprintf('Warning: Run %d, Harmonic %d only found %d valid macro-peaks.\n', r, h, length(pks));
        end
    end
end

%% Plotting - 4x3 Grid (Harmonics vs Bars)
figure('Name', 'Isolated Bar Comparison (Aligned Gradiometer Doublets)', 'Position', [50, 50, 1600, 1000]);
colors = lines(num_runs); 

for h = 1:num_harmonics
    for b = 1:num_bars
        subplot_idx = (h-1)*num_bars + b;
        subplot(num_harmonics, num_bars, subplot_idx);
        hold on;
        
        plot_data = squeeze(aligned_snippets(:, h, b, :)); 
        
        % Calculate Average and bounds
        avg_line = nanmean(plot_data, 1);
        upper_bound = avg_line * 1.10;
        lower_bound = avg_line * 0.90;
        
        % Draw +/- 10% Shaded Area
        fill([window_axis, fliplr(window_axis)], [upper_bound, fliplr(lower_bound)], ...
            [0.85 0.85 1], 'EdgeColor', 'none', 'FaceAlpha', 0.6, 'DisplayName', '+/- 10% Area');
        
        % Plot individual runs
        for r = 1:num_runs
            plot(window_axis, plot_data(r, :), 'Color', [colors(r,:) 0.5], ...
                'LineWidth', 1, 'DisplayName', folder_names{r});
        end
        
        % Plot Average Line
        plot(window_axis, avg_line, 'b-', 'LineWidth', 2.5, 'DisplayName', 'Average');
        
        title(sprintf('Harmonic %d: %s', h-1, bar_names{b}));
        grid on;
        xlim([-window_half_width, window_half_width]);
        
        if subplot_idx == 1
            legend('Location', 'northeast', 'FontSize', 8);
        end
        if h == num_harmonics
            xlabel('Samples from Macro-Peak Center');
        end
        if b == 1
            ylabel('Magnitude');
        end
    end
end

%% Console Output Analysis: Comparing Invariance
fprintf('\n=======================================================\n');
fprintf('GRADIOMETER INVARIANCE ANALYSIS (Averaged across %d runs)\n', num_runs);
fprintf('=======================================================\n');

focus_h = 2; % Evaluating Harmonic 1 

fprintf('\n--- 1. Single Frequency Phase Angle (H1) ---\n');
avg_phases = squeeze(nanmean(peak_phases(:, focus_h, :), 1));
std_phases = squeeze(nanstd(peak_phases(:, focus_h, :), 0, 1));
for b = 1:num_bars
    fprintf('%s: Mean Phase = %7.2f° | Variance = ±%.2f°\n', bar_names{b}, avg_phases(b), std_phases(b));
end

% Multi-Frequency Phase Differential Analysis
% Subtracting a low frequency phase from a high frequency phase isolates the material's 
% skin depth delay, mathematically cancelling out the physical distance (lift-off) delay.
fprintf('\n--- 2. Multi-Frequency Phase Differential (H1 Phase - H3 Phase) ---\n');
h_high = 2; % Harmonic 1
h_low  = 4; % Harmonic 3

% Calculate differential and normalize to -180 to 180 degrees
phase_diff_runs = peak_phases(:, h_high, :) - peak_phases(:, h_low, :);
phase_diff_runs = mod(phase_diff_runs + 180, 360) - 180; 

avg_phase_diff = squeeze(nanmean(phase_diff_runs, 1));
std_phase_diff = squeeze(nanstd(phase_diff_runs, 0, 1));

for b = 1:num_bars
    fprintf('%s: Diff (H1-H3) = %7.2f° | Variance = ±%.2f°\n', bar_names{b}, avg_phase_diff(b), std_phase_diff(b));
end

fprintf('\n--- 3. Area Under Curve (Speed Invariant) ---\n');
avg_areas = squeeze(nanmean(peak_areas(:, focus_h, :), 1));
std_areas = squeeze(nanstd(peak_areas(:, focus_h, :), 0, 1));
for b = 1:num_bars
    fprintf('%s: Mean Area = %8.1f | Variance = ±%.1f\n', bar_names{b}, avg_areas(b), std_areas(b));
end

fprintf('\n--- 4. Raw Macro-Peak Magnitude (Control) ---\n');
avg_mags = squeeze(nanmean(peak_magnitudes(:, focus_h, :), 1));
std_mags = squeeze(nanstd(peak_magnitudes(:, focus_h, :), 0, 1));
for b = 1:num_bars
    fprintf('%s: Mean Mag = %9.1f | Variance = ±%.1f\n', bar_names{b}, avg_mags(b), std_mags(b));
end
fprintf('=======================================================\n');