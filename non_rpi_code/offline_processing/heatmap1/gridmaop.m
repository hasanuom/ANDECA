% Eddy Current - Probabilistic Grid Mapping (Discrete Geometry)
clear; clc; close all;

%% 1. Configuration & File Loading
file_phase1 = 'no_drone_vicon_ndt_20260512_143339.csv'; 
file_phase2 = 'no_drone_vicon_ndt_20260512_143548.csv'; 

target_mag = 'magnitude_h2'; 

if ~isfile(file_phase1) || ~isfile(file_phase2)
    error('CSV files not found.');
end

T1 = readtable(file_phase1);
T2 = readtable(file_phase2);

%% 2. Extract and Convert Data (Meters to cm)
x1 = T1.x_m * 100;  y1 = T1.y_m * 100;  mag1 = T1.(target_mag);
x2 = T2.x_m * 100;  y2 = T2.y_m * 100;  mag2 = T2.(target_mag);

%% 3. Create Rigid, Discrete Grid
% We use a strict 1cm grid (no micro-smoothing)
grid_res = 1.0; 
min_x = floor(min([min(x1), min(x2)])); max_x = ceil(max([max(x1), max(x2)]));
min_y = floor(min([min(y1), min(y2)])); max_y = ceil(max([max(y1), max(y2)]));

[Xq, Yq] = meshgrid(min_x:grid_res:max_x, min_y:grid_res:max_y);

% Snap scattered data to the rigid grid using linear interpolation
F1 = scatteredInterpolant(x1, y1, mag1, 'linear', 'none');
F2 = scatteredInterpolant(x2, y2, mag2, 'linear', 'none');

V1 = F1(Xq, Yq);
V2 = F2(Xq, Yq);

%% 4. Baseline Correction
% Replace empty air (NaN) with the lowest recorded noise floor
baseline_val = min([min(mag1), min(mag2)]); 
V1(isnan(V1)) = baseline_val;
V2(isnan(V2)) = baseline_val;

% MAX merge to combine Phase 1 and Phase 2
V_raw = max(V1, V2);

%% 5. THE USER'S ALGORITHM: Straight Line Probability
% Calculate the sum of signals along every vertical column and horizontal row
col_sums = sum(V_raw, 1); % Profiles X-axis (Vertical lines)
row_sums = sum(V_raw, 2); % Profiles Y-axis (Horizontal lines)

% Normalize into a 0.0 to 1.0 Probability Scale
prob_vertical = (col_sums - min(col_sums)) ./ (max(col_sums) - min(col_sums));
prob_horizontal = (row_sums - min(row_sums)) ./ (max(row_sums) - min(row_sums));

% Extrapolate these 1D probabilities across the entire 2D grid
P_matrix_V = repmat(prob_vertical, size(V_raw, 1), 1);
P_matrix_H = repmat(prob_horizontal, 1, size(V_raw, 2));

% A specific 1cm block is highly probable if it belongs to EITHER a vertical or horizontal line
P_line = max(P_matrix_V, P_matrix_H);

%% 6. Bayesian Multiplication & Skirt Suppression
% Multiply the raw sensor data by the straight-line probability
V_enhanced = V_raw .* P_line;

% Optional: Square the result to heavily penalize the wide magnetic "skirts"
% This artificially shrinks the visual width closer to the physical rebar diameter
V_final = V_enhanced .^ 2; 

%% 7. Render Blocky Grid (No Smooth Curves)
figure('Name', 'Probabilistic Grid Map', 'Position', [100, 100, 900, 750]);

% Render as strict blocks
pcolor(Xq, Yq, V_final);

% shading flat ENSURES we see the rigid grid blocks, no smooth blurring
shading flat; 
colormap('jet'); 

cb = colorbar;
ylabel(cb, 'Probability-Weighted Magnitude', 'FontSize', 12, 'FontWeight', 'bold');

title('Probabilistic Grid Map (Discrete Structural Priors)', 'FontSize', 14);
xlabel('Vicon X Position (cm)', 'FontSize', 12);
ylabel('Vicon Y Position (cm)', 'FontSize', 12);

axis equal tight; 
set(gca, 'FontSize', 11);

% Draw the physical grid lines over the map
grid on;
set(gca, 'Layer', 'top', 'GridColor', [1 1 1], 'GridAlpha', 0.3);