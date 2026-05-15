% Eddy Current - Difference of Gaussians (DoG) Spatial Ridge Mapping
clear; clc; close all;

%% 1. Configuration & File Loading
vicon_dir = 'heatmap1';
file_phase1 = fullfile(vicon_dir, 'no_drone_vicon_ndt_20260512_143339.csv'); 
file_phase2 = fullfile(vicon_dir, 'no_drone_vicon_ndt_20260512_143548.csv'); 

target_mag = 'magnitude_h2'; 

if ~isfile(file_phase1) || ~isfile(file_phase2)
    error('Vicon CSV files not found.');
end

T1 = readtable(file_phase1);
T2 = readtable(file_phase2);

x1 = T1.x_m * 100;  y1 = T1.y_m * 100;  mag1 = T1.(target_mag);
x2 = T2.x_m * 100;  y2 = T2.y_m * 100;  mag2 = T2.(target_mag);

%% 2. Create High-Resolution Virtual Grid (0.5cm)
grid_res = 0.5; 
min_x = floor(min([min(x1), min(x2)])); max_x = ceil(max([max(x1), max(x2)]));
min_y = floor(min([min(y1), min(y2)])); max_y = ceil(max([max(y1), max(y2)]));

[Xq, Yq] = meshgrid(min_x:grid_res:max_x, min_y:grid_res:max_y);

%% 3. Map Raw Signal directly to Spatial Grid (Neutralizes Speed Variance)
F1 = scatteredInterpolant(x1, y1, mag1, 'linear', 'none');
F2 = scatteredInterpolant(x2, y2, mag2, 'linear', 'none');

V1 = F1(Xq, Yq);
V2 = F2(Xq, Yq);

baseline_val = min([min(mag1), min(mag2)]); 
V1(isnan(V1)) = baseline_val;
V2(isnan(V2)) = baseline_val;

% Merge taking maximum signal to preserve the Strong Axis
V_raw = max(V1, V2);

%% 4. The Difference of Gaussians (DoG) Spatial Filter
% This is the 2D equivalent of a matched filter. It hunts for "ridges"
% and mathematically deletes the wide magnetic skirts.

% Blur 1: Tight Gaussian (Captures the sharp physical centerline)
V_tight = imgaussfilt(V_raw, 1.5);

% Blur 2: Wide Gaussian (Captures ONLY the wide magnetic skirts)
V_wide = imgaussfilt(V_raw, 8.0);

% Subtract the skirts from the center to isolate the target presence
V_ridge = V_tight - V_wide;

% We only care about positive ridges (actual steel), not negative valleys
V_ridge = max(0, V_ridge);

%% 5. Clean up & Threshold
% Cut off the bottom 15% of the noise floor to leave a crisp image
threshold = max(V_ridge(:)) * 0.15;
V_ridge(V_ridge < threshold) = 0;

% Mask out areas you didn't physically fly the drone/sensor over
flight_mask = isnan(F1(Xq, Yq)) & isnan(F2(Xq, Yq));
V_ridge(flight_mask) = NaN;
V_ridge(V_ridge == 0) = NaN; % Make background clean

%% 6. Render the Heatmap
figure('Name', 'Spatial Ridge Detection (DoG)', 'Position', [100, 100, 900, 750]);

pcolor(Xq, Yq, V_ridge);
shading interp; 
colormap('jet'); 

cb = colorbar;
ylabel(cb, 'Target Ridge Intensity (Skirt Suppressed)', 'FontSize', 12, 'FontWeight', 'bold');

title(sprintf('Target Centerline Map (Spatial DoG Filter) - %s', target_mag), 'FontSize', 14);
xlabel('Vicon X Position (cm)', 'FontSize', 12);
ylabel('Vicon Y Position (cm)', 'FontSize', 12);

axis equal tight; 
set(gca, 'FontSize', 11, 'Color', [0.02 0.02 0.1]); 
grid on;
set(gca, 'Layer', 'top', 'GridColor', [1 1 1], 'GridAlpha', 0.15);