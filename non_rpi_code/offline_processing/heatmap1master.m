% Eddy Current - Matched Filter 2D Tomography (Curved-Geometry Safe)
clear; clc; close all;

%% 1. Configuration & File Loading
vicon_dir = 'heatmap1';
file_phase1 = fullfile(vicon_dir, 'no_drone_vicon_ndt_20260512_143339.csv'); 
file_phase2 = fullfile(vicon_dir, 'no_drone_vicon_ndt_20260512_143548.csv'); 

% The template will be pulled from here to match the 40mm lift-off profile
template_file = fullfile('measurements 40mm', 'run1', 'harmonics_2.csv');

target_mag = 'magnitude_h2'; 

if ~isfile(file_phase1) || ~isfile(file_phase2) || ~isfile(template_file)
    error('Required files not found. Check folder names and locations.');
end

%% 2. Extract Golden Template (12mm Bar from 40mm Run)
fprintf('Extracting Matched Filter Template...\n');
T_temp = readtable(template_file);
mag_clean = smoothdata(T_temp{:, 5}, 'movmedian', 15);
[mag_env, ~] = envelope(mag_clean, 40, 'peak');
mag_env(1:200) = 0; % Ignore startup noise

% Find the 12mm bar (last peak in the 40mm run)
[~, locs] = findpeaks(mag_env, 'MinPeakDistance', 100, 'MinPeakHeight', max(mag_env)*0.15);
if isempty(locs), error('Could not find template peak.'); end
center_idx = locs(end); 

% Extract a tight template (approx 120 packets wide)
template_half_width = 60;
template = mag_clean(center_idx - template_half_width : center_idx + template_half_width);
% Remove DC bias so the filter doesn't amplify flat noise
template = template - mean(template); 

%% 3. Load Vicon Data
T1 = readtable(file_phase1);
T2 = readtable(file_phase2);

x1 = T1.x_m * 100;  y1 = T1.y_m * 100;  mag1 = T1.(target_mag);
x2 = T2.x_m * 100;  y2 = T2.y_m * 100;  mag2 = T2.(target_mag);

%% 4. Apply 1D Matched Filter (Cross-Correlation Convolution)
fprintf('Applying Matched Filter to Vicon Time-Series...\n');

% Detrend Vicon data to remove baseline drift before filtering
mag1_detrend = mag1 - smoothdata(mag1, 'movmedian', 300);
mag2_detrend = mag2 - smoothdata(mag2, 'movmedian', 300);

% Convolve the data with the reversed template (Standard Matched Filter)
mf_out1 = conv(mag1_detrend, flipud(template), 'same');
mf_out2 = conv(mag2_detrend, flipud(template), 'same');

% Rectify: We only care about positive correlations (perfect matches)
mf_out1 = max(0, mf_out1);
mf_out2 = max(0, mf_out2);

%% 5. Create High-Resolution Virtual Grid (0.5cm)
min_x = floor(min([min(x1), min(x2)])); max_x = ceil(max([max(x1), max(x2)]));
min_y = floor(min([min(y1), min(y2)])); max_y = ceil(max([max(y1), max(y2)]));

[Xq, Yq] = meshgrid(min_x:0.5:max_x, min_y:0.5:max_y);

%% 6. Interpolate Filtered Data to 2D Spatial Map
% Using 'linear' to prevent mathematical ringing artifacts
F1 = scatteredInterpolant(x1, y1, mf_out1, 'linear', 'none');
F2 = scatteredInterpolant(x2, y2, mf_out2, 'linear', 'none');

V1 = F1(Xq, Yq);
V2 = F2(Xq, Yq);

% Fill un-flown areas with 0 (no correlation)
V1(isnan(V1)) = 0;
V2(isnan(V2)) = 0;

% Merge phases taking the maximum correlation (preserves strong axis)
V_combined = max(V1, V2);

%% 7. Final Visual Smoothing
% A tiny Gaussian blur (sigma=1.5) just connects the 4cm scan gaps 
% into continuous lines, perfectly preserving any real-world curves.
V_final = imgaussfilt(V_combined, 1.5);

% Crop out areas where the drone didn't physically fly
flight_mask = isnan(F1(Xq, Yq)) & isnan(F2(Xq, Yq));
V_final(flight_mask) = NaN; 

%% 8. Render the Heatmap
figure('Name', 'Matched Filter Tomography', 'Position', [100, 100, 900, 750]);

pcolor(Xq, Yq, V_final);
shading interp; % Smooth gradients 
colormap('jet'); 

cb = colorbar;
ylabel(cb, 'Matched Filter Correlation Strength', 'FontSize', 12, 'FontWeight', 'bold');

title('Matched Filter 2D Tomography (Curvature Safe)', 'FontSize', 14);
xlabel('Vicon X Position (cm)', 'FontSize', 12);
ylabel('Vicon Y Position (cm)', 'FontSize', 12);

axis equal tight; 
set(gca, 'FontSize', 11, 'Color', [0.05 0.05 0.15]);
grid on;
set(gca, 'Layer', 'top', 'GridColor', [1 1 1], 'GridAlpha', 0.2);
fprintf('Done.\n');