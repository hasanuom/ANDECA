% Eddy Current - High-Contrast Thresholded C-Scan
clear; clc; close all;
%% 1. Configuration & File Loading
vicon_dir = fullfile('Desktop', 'uni', 'ANDECA', 'measurements', 'heatmap2');
file_phase1 = fullfile(vicon_dir, 'no_drone_vicon_ndt_20260513_125930.csv'); 
file_phase2 = fullfile(vicon_dir, 'no_drone_vicon_ndt_20260513_125554.csv'); 
target_mag = 'magnitude_h2'; 
if ~isfile(file_phase1) || ~isfile(file_phase2)
    error('CSV files not found.');
end
T1 = readtable(file_phase1);
T2 = readtable(file_phase2);
x1 = T1.x_m * 100;  y1 = T1.y_m * 100;  mag1 = T1.(target_mag);
x2 = T2.x_m * 100;  y2 = T2.y_m * 100;  mag2 = T2.(target_mag);
%% 2. Create High-Resolution Virtual Grid
grid_res = 0.5; % 0.5 cm pixel resolution
min_x = floor(min([min(x1), min(x2)])); max_x = ceil(max([max(x1), max(x2)]));
min_y = floor(min([min(y1), min(y2)])); max_y = ceil(max([max(y1), max(y2)]));
[Xq, Yq] = meshgrid(min_x:grid_res:max_x, min_y:grid_res:max_y);
%% 3. Scattered Interpolation
F1 = scatteredInterpolant(x1, y1, mag1, 'linear', 'none');
F2 = scatteredInterpolant(x2, y2, mag2, 'linear', 'none');
V1 = F1(Xq, Yq);
V2 = F2(Xq, Yq);
%% 4. Baseline Correction & Merge
baseline_val = min([min(mag1), min(mag2)]); 
mask1 = isnan(V1);
mask2 = isnan(V2);
V1_fill = V1; V1_fill(mask1) = baseline_val;
V2_fill = V2; V2_fill(mask2) = baseline_val;
% Preserves the Strong Axis of the D-coil
V_combined = max(V1_fill, V2_fill);
%% 5. Spatial Smoothing (Bridge the 4cm gaps)
% A sigma of 2.5 smooths the "shaky hand" artifacts and connects the lines
V_smoothed = imgaussfilt(V_combined, 2.5);
%% 6. SKIRT SUPPRESSION (High-Pass Thresholding)
% Find the absolute peak of the strongest bar
max_sig = max(V_smoothed(:));
% Set a threshold to cut off the wide magnetic skirts (adjust between 0.3 to 0.5 if needed)
% 0.35 cuts out the bottom 35% of the signal energy, shrinking the visual width
threshold = max_sig * 0.35; 
% Snap anything below the threshold down to the baseline noise floor
V_smoothed(V_smoothed < threshold) = baseline_val;
%% 7. Clean up Edges
% Re-apply the empty air mask so we don't paint data outside your actual scan zone
V_smoothed(mask1 & mask2) = NaN; 
%% 8. Render the Heatmap
figure('Name', 'Thresholded Subsurface C-Scan', 'Position', [100, 100, 900, 750]);
pcolor(Xq, Yq, V_smoothed);
shading interp; 
colormap('jet'); 
cb = colorbar;
ylabel(cb, 'Thresholded Signal Magnitude', 'FontSize', 12, 'FontWeight', 'bold');
title(sprintf('High-Contrast Subsurface Map: \\pi-Shape (%s)', target_mag), 'FontSize', 14);
xlabel('Vicon X Position (cm)', 'FontSize', 12);
ylabel('Vicon Y Position (cm)', 'FontSize', 12);
axis equal tight; 
set(gca, 'FontSize', 11, 'Color', [0 0 0.56]); % Matches the deep blue of the Jet colormap floor
grid on;