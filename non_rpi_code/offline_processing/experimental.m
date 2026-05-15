% Eddy Current - Ultimate Master Alignment (30mm, 40mm, 50mm)
clear; clc; close all;

%% Configuration Parameters
num_harmonics = 4;
bar_names = {'12mm Bar', '8mm Bar', '6mm Bar'};
num_bars = length(bar_names);
test_folders = {'measurements 30mm', 'measurements 40mm', 'measurements 50mm'};

% --- Signal Processing Parameters ---
ignore_initial_samples = 200; 
smooth_window = 15;           
envelope_window = 50;         
min_distance = 100;           

% ZOOMED IN WINDOWS: Prevents adjacent bars from bleeding into the plots
rough_half_width = 120; 
window_half_width = 80;      
window_axis = -window_half_width : window_half_width;

%% Phase 1: Extract the "Golden Template" (from 30mm / run1)
fprintf('Extracting Golden Template from 30mm / run1...\n');
golden_templates = NaN(num_harmonics, num_bars, (rough_half_width*2)+1);
template_dir = fullfile(test_folders{1}, 'run1');

for h = 0:(num_harmonics-1)
    filename = fullfile(template_dir, sprintf('harmonics_%d.csv', h));
    if ~isfile(filename), error('Golden template file missing: %s', filename); end
    
    T = readtable(filename);
    mag_clean = smoothdata(T{:, 5}, 'movmedian', smooth_window);
    
    [mag_envelope, ~] = envelope(mag_clean, envelope_window, 'peak');
    mag_envelope(1:min(ignore_initial_samples, length(mag_envelope))) = 0; 
    min_height = max(mag_envelope) * 0.15;
    
    [~, locs] = findpeaks(mag_envelope, 'MinPeakDistance', 150, 'MinPeakHeight', min_height);
    
    if length(locs) >= num_bars
        % Always take the last 3 peaks to completely bypass start-up hand noise
        locs = locs((end-num_bars+1):end);
        
        for b = 1:num_bars
            rough_center = locs(b);
            rough_axis = -rough_half_width : rough_half_width;
            for w_idx = 1:length(rough_axis)
                target_idx = rough_center + rough_axis(w_idx);
                if target_idx > 0 && target_idx <= length(mag_clean)
                    golden_templates(h+1, b, w_idx) = mag_clean(target_idx);
                else
                    golden_templates(h+1, b, w_idx) = 0; 
                end
            end
        end
    else
        error('Template extraction failed for Harmonic %d.', h);
    end
end

%% Phase 2: Process All Test Folders
for f = 1:length(test_folders)
    current_test = test_folders{f};
    
    items = dir(fullfile(current_test, 'run*'));
    run_folders = {items([items.isdir]).name};
    num_runs = length(run_folders);
    
    if num_runs == 0
        fprintf('Skipping %s (No runs found)\n', current_test);
        continue;
    end
    
    fprintf('\nProcessing %s...\n', current_test);
    
    aligned_snippets = NaN(num_runs, num_harmonics, num_bars, length(window_axis));
    peak_magnitudes  = NaN(num_runs, num_harmonics, num_bars);
    peak_areas       = NaN(num_runs, num_harmonics, num_bars);
    peak_phases      = NaN(num_runs, num_harmonics, num_bars);
    
    for r = 1:num_runs
        run_path = fullfile(current_test, run_folders{r});
        
        for h = 0:(num_harmonics-1)
            filename = fullfile(run_path, sprintf('harmonics_%d.csv', h));
            if ~isfile(filename), continue; end
            
            T = readtable(filename);
            real_comp = T{:, 3}; imag_comp = T{:, 4}; magnitude = T{:, 5}; 
            
            phase_rad = unwrap(atan2(imag_comp, real_comp));
            phase_deg = rad2deg(phase_rad);
            
            mag_clean = smoothdata(magnitude, 'movmedian', smooth_window);
            [mag_envelope, ~] = envelope(mag_clean, envelope_window, 'peak');
            mag_envelope(1:min(ignore_initial_samples, length(mag_envelope))) = 0; 
            
            max_env = max(mag_envelope);
            if max_env <= 0 || isnan(max_env), continue; end
            
            % 5% threshold catches the highly attenuated 6mm bar at 40mm and 50mm
            min_height = max_env * 0.05; 
            [~, locs] = findpeaks(mag_envelope, 'MinPeakDistance', min_distance, 'MinPeakHeight', min_height);
                
            if length(locs) >= num_bars
                % Always take the last 3 peaks to bypass start-up noise
                locs = locs((end-num_bars+1):end);
                
                for b = 1:num_bars
                    rough_center = locs(b);
                    
                    noisy_target = zeros(1, (rough_half_width*2)+1);
                    rough_axis = -rough_half_width : rough_half_width;
                    for w_idx = 1:length(rough_axis)
                        target_idx = rough_center + rough_axis(w_idx);
                        if target_idx > 0 && target_idx <= length(mag_clean)
                            noisy_target(w_idx) = mag_clean(target_idx);
                        end
                    end
                    
                    template = squeeze(golden_templates(h+1, b, :))';
                    
                    [c, lags] = xcorr(template, noisy_target);
                    
                    % Constrained shift to prevent alignment wrap-around
                    valid_mask = (lags >= -80) & (lags <= 80);
                    c_valid = c(valid_mask);
                    lags_valid = lags(valid_mask);
                    
                    [~, max_idx] = max(c_valid);
                    shift_val = lags_valid(max_idx);
                    
                    shifted_target = circshift(noisy_target, shift_val);
                    
                    center_idx = rough_half_width + 1;
                    crop_range = (center_idx - window_half_width) : (center_idx + window_half_width);
                    final_snippet = shifted_target(crop_range);
                    
                    aligned_snippets(r, h+1, b, :) = final_snippet;
                    peak_areas(r, h+1, b) = trapz(max(final_snippet, 0));
                    
                    [~, max_idx_in_snippet] = max(final_snippet);
                    true_peak_global_idx = rough_center - shift_val - window_half_width + max_idx_in_snippet - 1;
                    true_peak_global_idx = max(1, min(length(mag_clean), true_peak_global_idx));
                    
                    peak_magnitudes(r, h+1, b) = mag_clean(true_peak_global_idx);
                    peak_phases(r, h+1, b)     = phase_deg(true_peak_global_idx);
                end
            else
                 fprintf('  -> Warning: %s Harmonic %d skipped. Only found %d bars.\n', run_folders{r}, h, length(locs));
            end
        end
    end
    
    %% Plotting - 4x3 Grid for Current Folder
    figure('Name', sprintf('Isolated Bars: %s', current_test), 'Position', [50, 50, 1600, 1000]);
    colors = lines(num_runs); 
    for h = 1:num_harmonics
        for b = 1:num_bars
            subplot_idx = (h-1)*num_bars + b;
            subplot(num_harmonics, num_bars, subplot_idx);
            hold on;
            
            plot_data = reshape(aligned_snippets(:, h, b, :), [num_runs, length(window_axis)]); 
            
            avg_line = nanmean(plot_data, 1);
            upper_bound = avg_line * 1.10;
            lower_bound = avg_line * 0.90;
            
            fill([window_axis, fliplr(window_axis)], [upper_bound, fliplr(lower_bound)], ...
                [0.85 0.85 1], 'EdgeColor', 'none', 'FaceAlpha', 0.6, 'DisplayName', '+/- 10% Area');
            
            for r = 1:num_runs
                plot(window_axis, plot_data(r, :), 'Color', [colors(r,:) 0.5], ...
                    'LineWidth', 1, 'DisplayName', run_folders{r});
            end
            
            plot(window_axis, avg_line, 'b-', 'LineWidth', 2.5, 'DisplayName', 'Average');
            
            title(sprintf('Harmonic %d: %s', h-1, bar_names{b}));
            grid on; xlim([-window_half_width, window_half_width]);
            if subplot_idx == 1, legend('Location', 'northeast', 'FontSize', 8); end
        end
    end
    
    %% Console Output Analysis for Current Folder
    fprintf('\n=======================================================\n');
    fprintf('ANALYSIS: %s (Averaged across %d runs)\n', current_test, num_runs);
    fprintf('=======================================================\n');
    
    focus_h = 2; % Harmonic 1
    
    fprintf('\n--- 1. Multi-Freq Phase Differential (H1 Phase - H3 Phase) ---\n');
    h_high = 2; h_low = 4; 
    phase_diff_runs = peak_phases(:, h_high, :) - peak_phases(:, h_low, :);
    
    phase_diff_rads = deg2rad(phase_diff_runs);
    R = squeeze(nanmean(exp(1i * phase_diff_rads), 1));
    avg_phase_diff_wrapped = rad2deg(angle(R));
    std_phase_diff = rad2deg(sqrt(max(0, -2 * log(abs(R))))); 
    
    for b = 1:num_bars
        fprintf('%s: Diff (H1-H3) = %7.2f° | Variance = ±%.2f°\n', bar_names{b}, avg_phase_diff_wrapped(b), std_phase_diff(b));
    end
    
    fprintf('\n--- 2. Area Ratios (H1 Area / H3 Area) ---\n');
    ratio_runs = peak_areas(:, h_high, :) ./ peak_areas(:, h_low, :);
    avg_ratios = squeeze(nanmean(ratio_runs, 1));
    std_ratios = squeeze(nanstd(ratio_runs, 0, 1));
    for b = 1:num_bars
        fprintf('%s: Ratio = %7.2f | Variance = ±%.2f\n', bar_names{b}, avg_ratios(b), std_ratios(b));
    end
    
    fprintf('\n--- 3. Raw First Peak Magnitude (Control Metric) ---\n');
    avg_mags = squeeze(nanmean(peak_magnitudes(:, focus_h, :), 1));
    std_mags = squeeze(nanstd(peak_magnitudes(:, focus_h, :), 0, 1));
    for b = 1:num_bars
        fprintf('%s: Mean Mag = %9.1f | Variance = ±%.1f\n', bar_names{b}, avg_mags(b), std_mags(b));
    end
end
fprintf('=======================================================\n');