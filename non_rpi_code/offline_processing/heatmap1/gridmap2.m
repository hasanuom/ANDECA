% Eddy Current - Orthogonal Centerline Projection (Rigid Grid)
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

x1 = T1.x_m * 100;  y1 = T1.y_m * 100;  mag1 = T1.(target_mag);
x2 = T2.x_m * 100;  y2 = T2.y_m * 100;  mag2 = T2.(target_mag);

%% 2. Create Rigid Base Grid (1cm Resolution)
grid_res = 1.0; 
min_x = floor(min([min(x1), min(x2)])); max_x = ceil(max([max(x1), max(x2)]));
min_y = floor(min([min(y1), min(y2)])); max_y = ceil(max([max(y1), max(y2)]));

[Xq, Yq] = meshgrid(min_x:grid_res:max_x, min_y:grid_res:max_y);

% Interpolate raw data to the 1cm grid
F1 = scatteredInterpolant(x1, y1, mag1, 'linear', 'none');
F2 = scatteredInterpolant(x2, y2, mag2, 'linear', 'none');

V1 = F1(Xq, Yq);
V2 = F2(Xq, Yq);

% Combine and replace empty air with the noise floor
baseline_val = min([min(mag1), min(mag2)]); 
flight_mask = isnan(V1) & isnan(V2); % Tracks where the drone actually flew

V1_fill = V1; V1_fill(isnan(V1)) = baseline_val;
V2_fill = V2; V2_fill(isnan(V2)) = baseline_val;

V_raw = max(V1_fill, V2_fill);

%% 3. The Structural Prior (1D Projection)
% We temporarily blur the data heavily. This ONLY serves to merge the 
% D-Coil "M" shape doublet into a single massive peak for the centerline finder.
V_smooth = imgaussfilt(V_raw, 4.0); 

% Compress the 2D map into 1D profiles by averaging down the axes
X_profile = mean(V_smooth, 1); % Finds vertical rebars
Y_profile = mean(V_smooth, 2); % Finds horizontal rebars

% Detrend to remove background noise
X_profile = X_profile - median(X_profile);
Y_profile = Y_profile - median(Y_profile);

%% 4. Centerline Ridge Detection
% mathematically find the true center of the steel
% 20% prominence ensures we only grab real steel, not floor noise
threshold_x = max(X_profile) * 0.20;
threshold_y = max(Y_profile) * 0.20;

[~, locs_x] = findpeaks(X_profile, 'MinPeakProminence', threshold_x, 'MinPeakDistance', 10);
[~, locs_y] = findpeaks(Y_profile, 'MinPeakProminence', threshold_y, 'MinPeakDistance', 10);

%% 5. Reconstruct Idealized Grid (Surgical Masking)
ideal_mask = zeros(size(V_raw));
line_thickness = 1; % 1 pixel radius = 3cm wide total line on the grid

% Draw perfectly straight vertical lines at the detected X coordinates
for i = 1:length(locs_x)
    idx = locs_x(i);
    ideal_mask(:, max(1, idx-line_thickness):min(size(ideal_mask,2), idx+line_thickness)) = 1;
end

% Draw perfectly straight horizontal lines at the detected Y coordinates
for i = 1:length(locs_y)
    idx = locs_y(i);
    ideal_mask(max(1, idx-line_thickness):min(size(ideal_mask,1), idx+line_thickness), :) = 1;
end

% Multiply the original raw magnitude data by our rigid straight-line mask
V_final = V_raw .* ideal_mask;

% Set the background to NaN so it plots as clean empty space
V_final(V_final == 0) = NaN;
V_final(flight_mask) = NaN; % Crop out areas where you didn't fly

%% 6. Render Final Orthogonal Map
figure('Name', 'Orthogonal Centerline Map', 'Position', [100, 100, 900, 750]);

pcolor(Xq, Yq, V_final);
shading flat; % Forces rigid, discrete grid blocks (no smooth blurring)
colormap('jet'); 

cb = colorbar;
ylabel(cb, 'Centerline Peak Magnitude', 'FontSize', 12, 'FontWeight', 'bold');

title('Orthogonal Centerline Map (1D Projection Priors)', 'FontSize', 14);
xlabel('Vicon X Position (cm)', 'FontSize', 12);
ylabel('Vicon Y Position (cm)', 'FontSize', 12);

axis equal tight; 
set(gca, 'FontSize', 11, 'Color', [0.05 0.05 0.15]); % Dark background makes the grid pop
grid on;
set(gca, 'Layer', 'top', 'GridColor', [1 1 1], 'GridAlpha', 0.2);