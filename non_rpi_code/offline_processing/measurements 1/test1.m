% Eddy Current Sensor Analysis
clear; clc; close all;

% Configuration
num_harmonics = 4;
% IMPORTANT: You may need to adjust 'min_distance' based on how fast you moved the sensor.
% This prevents the code from finding multiple peaks on the SAME bar.
min_distance_between_bars = 50; 

% Create a figure for the plots
figure('Name', 'Eddy Current Sensor: Bar Size Comparison', 'Position', [100, 100, 1200, 800]);

for i = 0:(num_harmonics-1)
    filename = sprintf('harmonics_%d.csv', i);
    
    % Check if file exists to prevent errors
    if ~isfile(filename)
        warning('File %s not found. Skipping.', filename);
        continue;
    end
    
    % Read the data. Using readtable handles the mixed datatypes (Col A is string)
    T = readtable(filename);
    
    % Extract relevant columns
    % Assuming Column 2 is Index and Column 5 is Magnitude based on the screenshot
    sample_index = T{:, 2}; 
    magnitude = T{:, 5};
    
    % --- Plotting the Raw Data ---
    subplot(num_harmonics, 1, i+1);
    plot(sample_index, magnitude, 'b-', 'LineWidth', 1.5);
    hold on;
    title(sprintf('Harmonic %d', i));
    xlabel('Sample Index');
    ylabel('Magnitude');
    grid on;
    
    % --- Peak Detection & Analysis ---
    % Find peaks in the signal. We sort by prominence to find the most obvious objects
    [pks, locs] = findpeaks(magnitude, 'SortStr', 'descend', 'MinPeakDistance', min_distance_between_bars);
    
    % We expect 3 objects (12mm, 8mm, 6mm), so we take the top 3 peaks found
    num_objects = min(3, length(pks));
    if num_objects < 3
        fprintf('Harmonic %d: Could only find %d distinct peaks. Try adjusting MinPeakDistance.\n', i, num_objects);
    end
    
    top_pks = pks(1:num_objects);
    top_locs = locs(1:num_objects);
    
    % Because we sorted by height to find them, we now need to sort them back
    % by TIME (index) so we know which peak is the 1st, 2nd, and 3rd bar you scanned.
    [sorted_locs, time_sort_idx] = sort(top_locs);
    sorted_pks = top_pks(time_sort_idx);
    
    % Plot red circles on the detected peaks
    plot(sample_index(sorted_locs), sorted_pks, 'ro', 'MarkerSize', 8, 'LineWidth', 2);
    
    % --- Console Output & Comparison ---
    fprintf('\n=======================================\n');
    fprintf('--- Analysis for Harmonic %d ---\n', i);
    
    if length(sorted_pks) == 3
        fprintf('1st object encountered (12mm bar) peak magnitude: %.4f\n', sorted_pks(1));
        fprintf('2nd object encountered (8mm bar)  peak magnitude: %.4f\n', sorted_pks(2));
        fprintf('3rd object encountered (6mm bar)  peak magnitude: %.4f\n', sorted_pks(3));
        
        % Logic to determine if it can tell the difference
        if (sorted_pks(1) > sorted_pks(2)) && (sorted_pks(2) > sorted_pks(3))
            fprintf('>>> SUCCESS: Sensor can differentiate. Signal scales linearly with size (12mm > 8mm > 6mm).\n');
        elseif (sorted_pks(1) ~= sorted_pks(2)) && (sorted_pks(2) ~= sorted_pks(3)) && (sorted_pks(1) ~= sorted_pks(3))
            fprintf('>>> PARTIAL: Sensor sees 3 different values, but they don''t scale perfectly by size. (Might be skin depth/frequency related).\n');
        else
             fprintf('>>> FAIL: Sensor cannot clearly differentiate between the sizes at this harmonic.\n');
        end
    else
        fprintf('Not enough peaks detected to run comparison.\n');
    end
end