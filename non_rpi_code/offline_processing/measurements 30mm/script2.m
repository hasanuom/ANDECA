% Eddy Current - Gradiometer Cross-Correlation Alignment & Phase Analysis
clear; clc; close all;

%% Configuration Parameters
num_harmonics = 4;
bar_names = {'12mm Bar', '8mm Bar', '6mm Bar'};
num_bars = length(bar_names);

% --- Signal Processing Parameters ---
ignore_initial_samples = 200; 
smooth_window = 15;           
envelope_window = 50;         
min_distance = 200;           

% We extract a wide rough window first, then slice the exact center after correlation
rough_half_width = 200; 
window_half_width = 120;      
window_axis = -window_half_width : window_half_width;

%% Find all Run folders
items = dir('run*');
folder_names = {items([items.isdir]).name};
num_runs = length(folder_names);

if num_runs == 0
    error('No folders starting with "run" were found.');
end

%% Data Storage Pre-allocation
rough_snippets   = NaN(num_runs, num_harmonics, num_bars, (rough_half_width*2)+1);
aligned_snippets = NaN(num_runs, num_harmonics, num_bars, length(window_axis));
peak_magnitudes  = NaN(num_runs, num_harmonics, num_bars);
peak_areas       = NaN(num_runs, num_harmonics, num_bars);
peak_phases      = NaN(num_runs, num_harmonics, num_bars);

%% Phase 1: Rough Extraction
for r = 1:num_runs
    current_folder = folder_names{r};
    
    for h = 0:(num_harmonics-1)
        filename = fullfile(current_folder, sprintf('harmonics_%d.csv', h));
        if ~isfile(filename), continue; end
        
        T = readtable(filename);
        
        real_comp = T{:, 3}; 
        imag_comp = T{:, 4}; 
        magnitude = T{:, 5}; 
        
        phase_rad = unwrap(atan2(imag_comp, real_comp));
        phase_deg = rad2deg(phase_rad);
        
        mag_clean = smoothdata(magnitude, 'movmedian', smooth_window);
        [mag_envelope, ~] = envelope(mag_clean, envelope_window, 'peak');
        mag_envelope(1:min(ignore_initial_samples, length(mag_envelope))) = 0; 
        
        max_env = max(mag_envelope);
        if max_env <= 0 || isnan(max_env), continue; end
        min_height = max_env * 0.15;
        
        [~, locs] = findpeaks(mag_envelope, 'MinPeakDistance', min_distance, 'MinPeakHeight', min_height);
            
        if length(locs) >= num_bars
            for b = 1:num_bars
                rough_center = locs(b);
                
                % Extract a wide rough snippet
                rough_axis = -rough_half_width : rough_half_width;
                for w_idx = 1:length(rough_axis)
                    target_idx = rough_center + rough_axis(w_idx);
                    if target_idx > 0 && target_idx <= length(mag_clean)
                        rough_snippets(r, h+1, b, w_idx) = mag_clean(target_idx);
                    else
                        rough_snippets(r, h+1, b, w_idx) = 0; % Pad with zero if out of bounds
                    end
                end
                
                % Phase is read near the highest raw peak within the rough window
                local_window = mag_clean(max(1, rough_center - 80) : min(length(mag_clean), rough_center + 80));
                [~, max_idx] = max(local_window);
                true_peak_idx = max(1, rough_center - 80) + max_idx - 1;
                
                peak_magnitudes(r, h+1, b) = mag_clean(true_peak_idx);
                peak_phases(r, h+1, b)     = phase_deg(true_peak_idx);
            end
        end
    end
end

%% Phase 2: Cross-Correlation Alignment
for h = 1:num_harmonics
    for b = 1:num_bars
        % Use Run 1 as the master template for shape alignment
        template = squeeze(rough_snippets(1, h, b, :));
        
        % Prevent correlation errors on completely empty data
        if all(isnan(template) | template == 0), continue; end 
        
        for r = 1:num_runs
            target = squeeze(rough_snippets(r, h, b, :));
            
            if r == 1
                shift_val = 0; % Template doesn't shift itself
            else
                % Cross-correlate target against template to find the optimal shift lag
                [c, lags] = xcorr(template, target);
                [~, I] = max(c);
                shift_val = lags(I);
            end
            
            % Apply shift and extract the final exact window
            shifted_target = circshift(target, shift_val);
            
            % Crop down from the rough window to the precise viewing window
            center_idx = rough_half_width + 1;
            crop_range = (center_idx - window_half_width) : (center_idx + window_half_width);
            
            final_snippet = shifted_target(crop_range);
            aligned_snippets(r, h, b, :) = final_snippet;
            
            % Calculate Area Under Curve
            peak_areas(r, h, b) = trapz(final_snippet);
        end
    end
end

%% Plotting - 4x3 Grid
figure('Name', 'Isolated Bar Comparison (Cross-Correlation Aligned)', 'Position', [50, 50, 1600, 1000]);
colors = lines(num_runs); 

for h = 1:num_harmonics
    for b = 1:num_bars
        subplot_idx = (h-1)*num_bars + b;
        subplot(num_harmonics, num_bars, subplot_idx);
        hold on;
        
        plot_data = squeeze(aligned_snippets(:, h, b, :)); 
        
        avg_line = nanmean(plot_data, 1);
        upper_bound = avg_line * 1.10;
        lower_bound = avg_line * 0.90;
        
        fill([window_axis, fliplr(window_axis)], [upper_bound, fliplr(lower_bound)], ...
            [0.85 0.85 1], 'EdgeColor', 'none', 'FaceAlpha', 0.6, 'DisplayName', '+/- 10% Area');
        
        for r = 1:num_runs
            plot(window_axis, plot_data(r, :), 'Color', [colors(r,:) 0.5], ...
                'LineWidth', 1, 'DisplayName', folder_names{r});
        end
        
        plot(window_axis, avg_line, 'b-', 'LineWidth', 2.5, 'DisplayName', 'Average');
        
        title(sprintf('Harmonic %d: %s', h-1, bar_names{b}));
        grid on;
        xlim([-window_half_width, window_half_width]);
        
        if subplot_idx == 1
            legend('Location', 'northeast', 'FontSize', 8);
        end
        if h == num_harmonics
            xlabel('Samples from Aligned Center');
        end
        if b == 1
            ylabel('Magnitude');
        end
    end
end

%% Console Output Analysis
fprintf('\n=======================================================\n');
fprintf('GRADIOMETER INVARIANCE ANALYSIS (Averaged across %d runs)\n', num_runs);
fprintf('=======================================================\n');

focus_h = 2; 

fprintf('\n--- 1. Single Frequency Phase Angle at 1st Peak (H1) ---\n');
avg_phases = squeeze(nanmean(peak_phases(:, focus_h, :), 1));
std_phases = squeeze(nanstd(peak_phases(:, focus_h, :), 0, 1));
for b = 1:num_bars
    fprintf('%s: Mean Phase = %7.2f° | Variance = ±%.2f°\n', bar_names{b}, avg_phases(b), std_phases(b));
end

fprintf('\n--- 2. Multi-Frequency Phase Differential (H1 Phase - H3 Phase) ---\n');
h_high = 2; 
h_low  = 4; 

phase_diff_runs = peak_phases(:, h_high, :) - peak_phases(:, h_low, :);
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

fprintf('\n--- 4. First Peak Magnitude (Control) ---\n');
avg_mags = squeeze(nanmean(peak_magnitudes(:, focus_h, :), 1));
std_mags = squeeze(nanstd(peak_magnitudes(:, focus_h, :), 0, 1));
for b = 1:num_bars
    fprintf('%s: Mean Mag = %9.1f | Variance = ±%.1f\n', bar_names{b}, avg_mags(b), std_mags(b));
end
fprintf('=======================================================\n');