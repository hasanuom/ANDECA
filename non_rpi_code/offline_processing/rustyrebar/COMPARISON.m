% Eddy Current - Single-Run Side-by-Side Rust Comparison
clear; clc; close all;

%% Configuration
target_dir = 'Run2COMPARISON';

if ~isfolder(target_dir)
    error('Directory "%s" not found. Ensure it is in the current working directory.', target_dir);
end

% --- Signal Processing Parameters ---
smooth_window = 15;           
baseline_window = 500; 
integration_half_width = 300; 

% --- Sweep Detection Parameters ---
tracker_window = 100; 
min_sweep_distance = 300; % Large distance to ensure we only catch the two main passes

%% Processing Loop
areas = zeros(4, 2);  % [Harmonic, Sweep(Clean=1, Rusty=2)]
phases = zeros(4, 2);

figure('Name', 'Side-by-Side Target Classification', 'Position', [100, 100, 1200, 500]);

for h = 0:3
    filename = fullfile(target_dir, sprintf('harmonics_%d.csv', h));
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
    
    % Track sweeps
    sweep_tracker = smoothdata(abs(mag_clean), 'movmean', tracker_window);
    min_sweep_height = max(sweep_tracker) * 0.15; 
    
    [~, sweep_locs] = findpeaks(sweep_tracker, ...
        'MinPeakDistance', min_sweep_distance, ...
        'MinPeakHeight', min_sweep_height);
        
    if length(sweep_locs) < 2
        error('Could not detect two distinct sweeps in Harmonic %d. Ensure a clear baseline gap between passes.', h);
    end
    
    % We only want the first two detected passes (1=Clean, 2=Rusty)
    sweep_locs = sweep_locs(1:2);
    
    for s = 1:2
        center = sweep_locs(s);
        
        start_idx = max(1, center - integration_half_width);
        end_idx = min(length(mag_clean), center + integration_half_width);
        window_range = start_idx:end_idx;
        
        local_sig = mag_clean(window_range);
        
        % Re-center on the exact true peak within the window
        [~, local_max_idx] = max(local_sig);
        true_peak_global = start_idx + local_max_idx - 1;
        
        local_sig_positive = max(local_sig, 0); 
        
        areas(h+1, s) = trapz(local_sig_positive);
        phases(h+1, s) = phase_deg(true_peak_global);
        
        if h == 1 % Plot Harmonic 1 for visual confirmation
            hold on;
            if s == 1
                color = 'b'; label = 'Clean 12mm';
            else
                color = 'r'; label = 'Rusty 12mm';
            end
            plot(window_range, local_sig, 'Color', color, 'LineWidth', 1.5, 'DisplayName', label);
            fill([window_range, fliplr(window_range)], [local_sig_positive', zeros(1, length(local_sig_positive))], ...
                color, 'FaceAlpha', 0.2, 'EdgeColor', 'none', 'HandleVisibility', 'off');
        end
    end
    
    if h == 1
        title('Harmonic 1: Single-Run Continuous Comparison');
        xlabel('Packet #'); ylabel('Magnitude');
        grid on; legend('Location', 'northeast');
    end
end

%% Extract Classifiers and Console Output
h1_idx = 2; h3_idx = 4;

clean_auc = areas(h1_idx, 1);
rusty_auc = areas(h1_idx, 2);

clean_phase_diff = mod((phases(h1_idx, 1) - phases(h3_idx, 1)) + 180, 360) - 180;
rusty_phase_diff = mod((phases(h1_idx, 2) - phases(h3_idx, 2)) + 180, 360) - 180;

clean_ratio = areas(h1_idx, 1) / areas(h3_idx, 1);
rusty_ratio = areas(h1_idx, 2) / areas(h3_idx, 2);

fprintf('\n=======================================================\n');
fprintf('SIDE-BY-SIDE RUST IMPACT ANALYSIS\n');
fprintf('=======================================================\n');

fprintf('--- 1. Clean 12mm Baseline ---\n');
fprintf('AUC (H1):           %8.1f\n', clean_auc);
fprintf('Phase Diff (H1-H3): %6.2f°\n', clean_phase_diff);
fprintf('Area Ratio (H1/H3): %6.2f\n\n', clean_ratio);

fprintf('--- 2. Rusty 12mm Target ---\n');
fprintf('AUC (H1):           %8.1f\n', rusty_auc);
fprintf('Phase Diff (H1-H3): %6.2f°\n', rusty_phase_diff);
fprintf('Area Ratio (H1/H3): %6.2f\n\n', rusty_ratio);

auc_shift_pct = ((rusty_auc - clean_auc) / clean_auc) * 100;
ratio_shift_pct = abs(rusty_ratio - clean_ratio) / clean_ratio * 100;

fprintf('--- Oxidation Impact Summary ---\n');
fprintf('Signal Loss (AUC Drop): %+.1f%%\n', auc_shift_pct);
fprintf('Algorithmic Variance (Ratio Shift): ±%.1f%%\n', ratio_shift_pct);

if ratio_shift_pct <= 10.0
    fprintf('\n>> STATUS: SUCCESS. The Ratio/Phase algorithmic metrics successfully penetrated the oxide layer and identified the target core.\n');
else
    fprintf('\n>> STATUS: DEVIATION. The oxidation layer was severe enough to skew the core identification metrics.\n');
end
fprintf('=======================================================\n');