% Eddy Current - Multi-Session Global Spatial Mapping (DoG)
clear; clc; close all;

%% 1. Configuration & File Loading
target_mag = 'magnitude_h2'; 

% Heatmap 1 Files (Yesterday)
dir1 = 'heatmap1';
file1_p1 = fullfile(dir1, 'no_drone_vicon_ndt_20260512_143339.csv'); 
file1_p2 = fullfile(dir1, 'no_drone_vicon_ndt_20260512_143548.csv'); 

% Heatmap 2 Files (Today)
dir2 = 'heatmap2';
file2_p1 = fullfile(dir2, 'no_drone_vicon_ndt_20260513_125554.csv'); 
file2_p2 = fullfile(dir2, 'no_drone_vicon_ndt_20260513_125930.csv'); 

if ~isfile(file1_p1) || ~isfile(file2_p1)
    error('CSV files not found. Ensure heatmap1 and heatmap2 folders are in your current directory.');
end

% Load Data
fprintf('Loading data from heatmap1 and heatmap2...\n');
T1 = readtable(file1_p1); T2 = readtable(file1_p2);
T3 = readtable(file2_p1); T4 = readtable(file2_p2);

% Extract variables and convert meters to cm
x1 = T1.x_m * 100;  y1 = T1.y_m * 100;  mag1 = T1.(target_mag);
x2 = T2.x_m * 100;  y2 = T2.y_m * 100;  mag2 = T2.(target_mag);
x3 = T3.x_m * 100;  y3 = T3.y_m * 100;  mag3 = T3.(target_mag);
x4 = T4.x_m * 100;  y4 = T4.y_m * 100;  mag4 = T4.(target_mag);

%% 2. Create Global High-Resolution Virtual Grid (0.5cm)
% Find the absolute boundaries across ALL datasets
grid_res = 0.5; 
min_x = floor(min([x1; x2; x3; x4])); max_x = ceil(max([x1; x2; x3; x4]));
min_y = floor(min([y1; y2; y3; y4])); max_y = ceil(max([y1; y2; y3; y4]));

[Xq, Yq] = meshgrid(min_x:grid_res:max_x, min_y:grid_res:max_y);

%% 3. Map Raw Signal to Global Spatial Grid
fprintf('Interpolating scattered data to global spatial grid...\n');
F1 = scatteredInterpolant(x1, y1, mag1, 'linear', 'none');
F2 = scatteredInterpolant(x2, y2, mag2, 'linear', 'none');
F3 = scatteredInterpolant(x3, y3, mag3, 'linear', 'none');
F4 = scatteredInterpolant(x4, y4, mag4, 'linear', 'none');

V1 = F1(Xq, Yq); V2 = F2(Xq, Yq);
V3 = F3(Xq, Yq); V4 = F4(Xq, Yq);

% Find global baseline floor
baseline_val = min([mag1; mag2; mag3; mag4]); 

% Temporarily fill un-flown areas with the baseline noise floor for clean merging
V1_fill = V1; V1_fill(isnan(V1)) = baseline_val;
V2_fill = V2; V2_fill(isnan(V2)) = baseline_val;
V3_fill = V3; V3_fill(isnan(V3)) = baseline_val;
V4_fill = V4; V4_fill(isnan(V4)) = baseline_val;

% Merge all passes. The MAX function stacks all 4 layers and guarantees 
% the strongest D-Coil "hit" wins out, preserving all horizontal and vertical bars.
V_raw = max(cat(3, V1_fill, V2_fill, V3_fill, V4_fill), [], 3);

%% 4. The Difference of Gaussians (DoG) Spatial Filter
fprintf('Applying Difference of Gaussians (DoG) filter...\n');
V_tight = imgaussfilt(V_raw, 1.5);
V_wide  = imgaussfilt(V_raw, 8.0);
V_ridge = V_tight - V_wide;

% Strip out negative valleys (we only want positive steel ridges)
V_ridge = max(0, V_ridge);

%% 5. Clean up & Threshold
% Cut off the bottom 15% of the noise to isolate the crisp centerline
threshold = max(V_ridge(:)) * 0.15;
V_ridge(V_ridge < threshold) = 0;

% Global Flight Mask: ONLY hide a pixel if the drone didn't fly over it in ANY of the 4 passes
flight_mask = isnan(V1) & isnan(V2) & isnan(V3) & isnan(V4);
V_ridge(flight_mask) = NaN;
V_ridge(V_ridge == 0) = NaN; % Render background clean/transparent

%% 6. Render the Multi-Session Heatmap
fprintf('Rendering Map...\n');
figure('Name', 'Global Spatial Ridge Map', 'Position', [100, 100, 1000, 800]);

pcolor(Xq, Yq, V_ridge);
shading interp; 
colormap('jet'); 

cb = colorbar;
ylabel(cb, 'Target Ridge Intensity (Skirt Suppressed)', 'FontSize', 12, 'FontWeight', 'bold');

title(sprintf('Global Centerline Map (Sessions 1 & 2) - %s', target_mag), 'FontSize', 14);
xlabel('Vicon X Position (cm)', 'FontSize', 12);
ylabel('Vicon Y Position (cm)', 'FontSize', 12);

axis equal tight; 
set(gca, 'FontSize', 11, 'Color', [0.02 0.02 0.1]); 
grid on;
set(gca, 'Layer', 'top', 'GridColor', [1 1 1], 'GridAlpha', 0.15);
fprintf('Complete.\n');