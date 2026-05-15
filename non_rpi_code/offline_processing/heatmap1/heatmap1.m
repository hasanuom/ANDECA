% Eddy Current - 2D C-Scan Heatmap Generator ("Pi" Shape Target)
clear; clc; close all;

%% 1. Configuration & File Loading
file_phase1 = 'no_drone_vicon_ndt_20260512_143339.csv'; % X-Axis Sweeps
file_phase2 = 'no_drone_vicon_ndt_20260512_143548.csv'; % Y-Axis Sweeps

target_mag = 'magnitude_h2'; % Change to magnitude_h1 if 6mm is too faint on h2

if ~isfile(file_phase1) || ~isfile(file_phase2)
    error('CSV files not found. Ensure they are in the MATLAB current folder.');
end

T1 = readtable(file_phase1);
T2 = readtable(file_phase2);

%% 2. Extract and Convert Data (Meters to cm)
x1 = T1.x_m * 100;  y1 = T1.y_m * 100;  mag1 = T1.(target_mag);
x2 = T2.x_m * 100;  y2 = T2.y_m * 100;  mag2 = T2.(target_mag);

%% 3. Create High-Resolution Virtual Grid
min_x = min([min(x1), min(x2)]); max_x = max([max(x1), max(x2)]);
min_y = min([min(y1), min(y2)]); max_y = max([max(y1), max(y2)]);

grid_res = 0.5; % 0.5 cm pixel resolution
[Xq, Yq] = meshgrid(min_x:grid_res:max_x, min_y:grid_res:max_y);

%% 4. Scattered Interpolation (Linear prevents mathematical ringing)
F1 = scatteredInterpolant(x1, y1, mag1, 'linear', 'none');
F2 = scatteredInterpolant(x2, y2, mag2, 'linear', 'none');

V1 = F1(Xq, Yq);
V2 = F2(Xq, Yq);

%% 5. Robust Merge (Fixes missing chunks at intersections)
% Find the baseline noise floor of the environment to replace empty air
baseline_val = min([min(mag1), min(mag2)]); 

% Create masks of where the sensor actually physically traveled
mask1 = isnan(V1);
mask2 = isnan(V2);

% Temporarily fill empty air with baseline to allow mathematical merging
V1_fill = V1; V1_fill(mask1) = baseline_val;
V2_fill = V2; V2_fill(mask2) = baseline_val;

% MAX merge: Preserves the "Strong Axis" of the D-coil at the Pi intersections
V_combined = max(V1_fill, V2_fill);

%% 6. NDT Spatial Smoothing (Fixes the 4cm "Beading" effect)
% Apply a 2D Gaussian blur to simulate the continuous magnetic field footprint.
% A sigma of 2.5 perfectly bridges a 4cm manual sweep gap.
V_smoothed = imgaussfilt(V_combined, 2.5);

% Re-apply the empty air mask so we don't paint data outside your actual scan zone
V_smoothed(mask1 & mask2) = NaN; 

%% 7. Render the Heatmap
figure('Name', 'Eddy Current 2D C-Scan (Pi Shape)', 'Position', [100, 100, 900, 750]);

pcolor(Xq, Yq, V_smoothed);
shading interp; 
colormap('jet'); 

cb = colorbar;
ylabel(cb, 'Signal Magnitude', 'FontSize', 12, 'FontWeight', 'bold');

title(sprintf('2D Subsurface Map: \\pi-Shape Geometry (%s)', target_mag), 'FontSize', 14);
xlabel('Vicon X Position (cm)', 'FontSize', 12);
ylabel('Vicon Y Position (cm)', 'FontSize', 12);

axis equal tight; 
set(gca, 'FontSize', 11);
grid on;