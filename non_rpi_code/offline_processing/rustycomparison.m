% Eddy Current - Rusty Rebar vs Clean Rebar Classification
clear; clc; close all;

%% Configuration
% Point this to a clean 12mm baseline run for direct comparison
clean_dir = fullfile('measurements 30mm', 'run1'); 
rusty_dir = fullfile('rustyrebar', 'run1');

if ~isfolder(clean_dir) || ~isfolder(rusty_dir)
    error('Directories not found. Ensure "measurements 30mm\run1" and "rustyrebar\run1" exist.');
end

% --- Signal Processing Parameters ---
smooth_window = 15;           
baseline_window = 500; 
integration_half_width = 300; 

dirs = {clean_dir, rusty_dir};
labels = {'Clean 12mm Rebar', 'Rusty 12mm Rebar'};
results = struct();

figure('Name', 'Rusty vs Clean Target Classification', 'Position', [100, 100, 1200, 500]);

%% Processing Loop
for d = 1:2
    current_dir = dirs{d};
    
    areas = zeros(1, 4);
    phases = zeros(1, 4);
    
    for h = 0:3
        filename = fullfile(current_dir, sprintf('harmonics_%d.csv', h));
        if ~isfile(filename), continue; end
        
        T = readtable(filename);
        real_comp = T{:, 3}; 
        imag_comp = T{:, 4}; 
        magnitude = T{:, 5}; 
        
        phase_rad = unwrap(atan2(imag_comp, real_comp));
        phase_deg = rad2deg(phase_rad);
        
        baseline = smoothdata(magnitude, 'movmedian', baseline_window);
        mag_flat = magnitude - baseline;
        mag_clean = smoothdata(mag_flat, 'movmedian', smooth_window);
        
        % The absolute maximum naturally bypasses the flat parallel swipe
        [~, global_max_idx] = max(mag_clean);
        
        start_idx = max(1, global_max_idx - integration_half_width);
        end_idx = min(length(mag_clean), global_max_idx + integration_half_width);
        window_range = start_idx:end_idx;
        
        local_sig = mag_clean(window_range);
        local_sig_positive = max(local_sig, 0); 
        
        areas(h+1) = trapz(local_sig_positive);
        phases(h+1) = phase_deg(global_max_idx);
        
        if h == 1 % Plot Harmonic 1 for visual confirmation
            subplot(1, 2, d);
            plot(mag_clean, 'Color', [0.6 0.8 1], 'LineWidth', 1.5); hold on;
            fill([window_range, fliplr(window_range)], [local_sig_positive', zeros(1, length(local_sig_positive))], ...
                'b', 'FaceAlpha', 0.3, 'EdgeColor', 'none', 'DisplayName', 'Integration Area');
            title(labels{d});
            xlabel('Packet #'); ylabel('Magnitude (H1)');
            grid on;
        end
    end
    
    % Extract classifiers: H1 (Index 2) and H3 (Index 4)
    h1_idx = 2; h3_idx = 4;
    
    results(d).name = labels{d};
    results(d).AUC_H1 = areas(h1_idx);
    results(d).Phase_Diff = mod((phases(h1_idx) - phases(h3_idx)) + 180, 360) - 180;
    results(d).Area_Ratio = areas(h1_idx) / areas(h3_idx);
end

%% Console Output
fprintf('\n=======================================================\n');
fprintf('RUSTY REBAR CLASSIFICATION ANALYSIS\n');
fprintf('=======================================================\n');

for d = 1:2
    fprintf('--- %s ---\n', results(d).name);
    fprintf('Speed-Invariant AUC (H1): %8.1f\n', results(d).AUC_H1);
    fprintf('Phase Differential (H1-H3): %6.2f°\n', results(d).Phase_Diff);
    fprintf('Area Ratio (H1/H3):         %6.2f\n\n', results(d).Area_Ratio);
end

auc_diff_pct = abs(results(1).AUC_H1 - results(2).AUC_H1) / results(1).AUC_H1 * 100;

fprintf('--- Comparison ---\n');
fprintf('AUC Shift: %.1f%%\n', auc_diff_pct);

% Utilizing the established <15% variance threshold for manual speed sweeps
if auc_diff_pct <= 15.0
    fprintf('>> STATUS: SUCCESS. Target correctly classified as 12mm despite surface rust.\n');
else
    fprintf('>> STATUS: DEVIATION. Surface oxidation significantly altered the eddy current signature.\n');
end
fprintf('=======================================================\n');