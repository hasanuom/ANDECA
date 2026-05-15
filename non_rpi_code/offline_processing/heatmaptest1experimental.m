% ═══════════════════════════════════════════════════════════════════
% REBAR DETECTION v2 — Log10 + Smooth (no matched filter)
% Fix: lag=17, wider baseline, log-domain peak detection, DBSCAN
% ═══════════════════════════════════════════════════════════════════
clear; clc; close all;

%% ── CONFIG ────────────────────────────────────────────────────────
TARGET_FOLDER   = 'heatmap4';
TARGET_COL      = 'magnitude_h2';

LAG_SAMPLES     = 17;      % 340 ms @ your sample rate — CONFIRMED

GRID_RES_CM     = 0.2;    % 2 mm spatial grid (fast, still sharp)

% Baseline window: MUST be >> rebar spacing so it doesn't eat the signal.
% If your 3 rebars are ~15-20 cm apart, use at least 5× that = 100 cm.
BASELINE_WIN_CM = 100.0;

% Smooth window: collapse the raw triplet into ONE bump per rebar.
% ~1.5× your gradiometer baseline diameter.  Start at 10 cm, raise if
% you still see 3 sub-peaks per rebar crossing.
SMOOTH_WIN_CM   = 10.0;

% Minimum physical separation between adjacent rebars (cm)
MIN_SEP_CM      = 8.0;

% Peak prominence on the LOG10 smoothed signal.
% Log10(12 mm peak) ≈ 3.2,  log10(6 mm peak) ≈ 0.7.
% Prominence of 0.10 on log10 scale picks up even the 6 mm bar.
% Raise to 0.20 if you're getting too many false hits.
LOG_PROMINENCE  = 0.10;

% DBSCAN clustering — merges detections from many passes into one dot
CLUSTER_EPS_CM  = 4.0;    % raise to 6 if dots are spread more
CLUSTER_MINPTS  = 3;      % minimum pass-through detections per rebar

% ── Amplitude thresholds (RAW magnitude, NOT log) ─────────────────
% After first run: print unique(sort(rb_a)) to see your real values.
AMP_12MM = 500.0;
AMP_8MM  =  50.0;
AMP_6MM  =   5.0;
%% ─────────────────────────────────────────────────────────────────

%% 1. Find scan files
assert(isfolder(TARGET_FOLDER), 'Folder not found: %s', TARGET_FOLDER);
raw_list = dir(fullfile(TARGET_FOLDER, '*.csv'));
scan_files = {};
for i = 1:numel(raw_list)
    if ~any(contains(raw_list(i).name, {'_h0','_h1','_h2','_h3'}))
        scan_files{end+1} = fullfile(TARGET_FOLDER, raw_list(i).name);
    end
end
fprintf('Processing %d scan file(s)...\n', numel(scan_files));

%% 2. Main processing loop
all_px = [];  all_py = [];  all_pa = [];
path_x = [];  path_y = [];
diag   = [];   % save first productive pass for the diagnostic plot

for fi = 1:numel(scan_files)
    T   = readtable(scan_files{fi});
    x   = T.x_m * 100;            % m → cm
    y   = T.y_m * 100;
    mag = T.(TARGET_COL);

    if numel(mag) < 100, continue; end

    % ── Smooth Vicon jitter (position only) ──────────────────────
    x = smoothdata(x, 'gaussian', 5);
    y = smoothdata(y, 'gaussian', 5);

    % ── Lag correction (sample domain) ───────────────────────────
    %    Shift mag BACKWARD so it aligns with the position that was
    %    actually being logged 340 ms earlier.
    mag_c = circshift(mag, -LAG_SAMPLES);
    mag_c(end-LAG_SAMPLES+1 : end) = median(mag);

    path_x = [path_x; x; NaN];
    path_y = [path_y; y; NaN];

    % ── Arc-length → uniform 1D spatial grid ─────────────────────
    ds  = [0; hypot(diff(x), diff(y))];
    s   = cumsum(ds);
    [s_u, ui] = unique(s, 'stable');
    if s_u(end) < 20, continue; end   % skip trivially short paths

    s_reg   = (0 : GRID_RES_CM : s_u(end))';
    x_reg   = interp1(s_u, x(ui),      s_reg);
    y_reg   = interp1(s_u, y(ui),      s_reg);
    mag_reg = interp1(s_u, mag_c(ui),  s_reg);

    % ── Log10 transform ──────────────────────────────────────────
    %    Compresses the 12mm/6mm amplitude ratio from 300x → 2.5x,
    %    letting findpeaks see both with the same threshold.
    mag_log = log10(abs(mag_reg) + 1);

    % ── Baseline removal on log signal ───────────────────────────
    bwin     = round(BASELINE_WIN_CM / GRID_RES_CM);
    base_log = smoothdata(mag_log, 'gaussian', bwin);
    mag_dt   = mag_log - base_log;   % zero-mean, rebar bumps positive

    % ── Collapse triplet: smooth wider than the gradiometer lobe ─
    swin      = round(SMOOTH_WIN_CM / GRID_RES_CM);
    mag_sm    = smoothdata(mag_dt, 'gaussian', swin);
    mag_sm    = max(mag_sm, 0);      % discard negative residuals

    % ── Peak detection ───────────────────────────────────────────
    min_d  = round(MIN_SEP_CM / GRID_RES_CM);
    [pks, locs] = findpeaks(mag_sm, ...
        'MinPeakProminence', LOG_PROMINENCE, ...
        'MinPeakDistance',   min_d);

    for k = 1:numel(locs)
        idx = locs(k);
        raw_amp = mag_reg(idx);          % raw (non-log) for classification
        if raw_amp >= AMP_6MM
            all_px(end+1) = x_reg(idx);
            all_py(end+1) = y_reg(idx);
            all_pa(end+1) = raw_amp;
        end
    end

    % Save first pass with detections for diagnostic
    if isempty(diag) && numel(locs) > 0
        diag.s       = s_reg;
        diag.mag_raw = mag_reg;
        diag.mag_log = mag_log;
        diag.base    = base_log;
        diag.mag_dt  = mag_dt;
        diag.mag_sm  = mag_sm;
        diag.locs    = locs;
        diag.pks     = pks;
    end
end
fprintf('Raw detections: %d\n', numel(all_px));

%% 3. DBSCAN clustering → one dot per rebar position
rb_x = [];  rb_y = [];  rb_a = [];
if numel(all_px) >= CLUSTER_MINPTS
    pts    = [all_px(:), all_py(:)];
    labels = dbscan(pts, CLUSTER_EPS_CM, CLUSTER_MINPTS);

    n_clusters = max(labels);
    fprintf('Clusters found: %d\n', n_clusters);
    for c = 1:n_clusters
        m = (labels == c);
        rb_x(end+1) = median(all_px(m));
        rb_y(end+1) = median(all_py(m));
        rb_a(end+1) = median(all_pa(m));
    end
    % Unclustered but high-amplitude isolated detections (12mm likely)
noise = (labels.' == -1) & (all_pa >= AMP_8MM);
    rb_x  = [rb_x, all_px(noise)];
    rb_y  = [rb_y, all_py(noise)];
    rb_a  = [rb_a, all_pa(noise)];
else
    % Fallback: too few detections — plot raw
    rb_x = all_px;  rb_y = all_py;  rb_a = all_pa;
    fprintf('WARNING: too few detections for clustering. Check LAG_SAMPLES and LOG_PROMINENCE.\n');
end

% ── Print amplitude values to help you tune the thresholds ───────
fprintf('\n--- Detected rebar amplitudes (raw) ---\n');
fprintf('  Min: %.1f   Median: %.1f   Max: %.1f\n', ...
    min(rb_a), median(rb_a), max(rb_a));
fprintf('  All values: ');  fprintf('%.0f ', sort(rb_a,'descend'));  fprintf('\n');

%% 4. Classify
m12 = rb_a >= AMP_12MM;
m8  = rb_a >= AMP_8MM  & ~m12;
m6  = rb_a >= AMP_6MM  & ~m12 & ~m8;

fprintf('\n12mm: %d pts   8mm: %d pts   6mm: %d pts\n', ...
    sum(m12), sum(m8), sum(m6));

%% ══════════════════════════════════════════════════════════════════
%% FIGURE 1 — DIAGNOSTIC (one representative pass)
%% ══════════════════════════════════════════════════════════════════
if ~isempty(diag)
    bg = [0.04 0.04 0.10];  fg = [0.85 0.90 1.00];
    figure('Name','DIAGNOSTIC — 1D Pipeline','Position',[30 30 1150 820],'Color',bg);

    ax1 = subplot(4,1,1);
    plot(diag.s, diag.mag_raw, 'Color',[0.4 0.7 1.0], 'LineWidth', 0.8);
    title('① Raw magnitude (lag-corrected)','Color',fg);
    ylabel('Magnitude','Color',fg);
    set(ax1,'Color',bg,'XColor',fg,'YColor',fg,'GridColor',[.3 .3 .4]); grid on;

    ax2 = subplot(4,1,2);
    plot(diag.s, diag.mag_log, 'Color',[0.5 1.0 0.5], 'LineWidth', 0.8);
    hold on;
    plot(diag.s, diag.base, 'y--', 'LineWidth', 1.4);
    hold off;
    legend({'Log10 signal','Baseline (100 cm window)'},'TextColor',fg,'Color',bg,'Location','ne');
    title('② Log10 + baseline — should be a SLOW smooth curve below the peaks','Color',fg);
    ylabel('Log10','Color',fg);
    set(ax2,'Color',bg,'XColor',fg,'YColor',fg,'GridColor',[.3 .3 .4]); grid on;

    ax3 = subplot(4,1,3);
    plot(diag.s, diag.mag_dt, 'Color',[0.8 0.5 1.0], 'LineWidth', 0.8);
    hold on;
    plot(diag.s, diag.mag_sm, 'Color',[1 0.7 0.2], 'LineWidth', 1.8);
    yline(0,'w--');
    hold off;
    legend({'Detrended log','Smoothed (peak detector input)'},'TextColor',fg,'Color',bg,'Location','ne');
    title(sprintf('③ Detrended + smoothed (SMOOTH\\_WIN\\_CM=%.0f cm) — each rebar should be ONE smooth bump', ...
        SMOOTH_WIN_CM),'Color',fg);
    ylabel('Log residual','Color',fg);
    set(ax3,'Color',bg,'XColor',fg,'YColor',fg,'GridColor',[.3 .3 .4]); grid on;

    ax4 = subplot(4,1,4);
    plot(diag.s, diag.mag_sm, 'Color',[1 0.3 0.3], 'LineWidth', 1.2);
    hold on;
    if ~isempty(diag.locs)
        plot(diag.s(diag.locs), diag.pks, 'gv', 'MarkerSize', 11, 'MarkerFaceColor','g');
    end
    yline(LOG_PROMINENCE,'w--','Threshold','LabelVerticalAlignment','bottom');
    hold off;
    legend({'Smoothed signal','Detected peaks'},'TextColor',fg,'Color',bg,'Location','ne');
    title(sprintf('④ Peak detection — expect ~3 peaks per full perpendicular strip | LOG\\_PROMINENCE=%.2f', ...
        LOG_PROMINENCE),'Color',fg);
    xlabel('Arc distance (cm)','Color',fg); ylabel('Log residual','Color',fg);
    set(ax4,'Color',bg,'XColor',fg,'YColor',fg,'GridColor',[.3 .3 .4]); grid on;

    linkaxes([ax1 ax2 ax3 ax4], 'x');
end

%% ══════════════════════════════════════════════════════════════════
%% FIGURE 2 — REBAR MAP
%% ══════════════════════════════════════════════════════════════════
figure('Name','Rebar Detection Map','Position',[250 100 1000 850],'Color','k');
ax = axes; hold(ax,'on');

plot(ax, path_x, path_y, 'Color',[.22 .22 .32],'LineWidth',.7,'HandleVisibility','off');

COLS = {[1 0.1 0.1], [1 0.55 0.05], [0.15 0.85 0.95]};
SZ   = [230, 110, 55];
LBL  = {'12 mm rebar','8 mm rebar','6 mm rebar'};
MASKS = {m12, m8, m6};

for i = 1:3
    if any(MASKS{i})
        scatter(ax, rb_x(MASKS{i}), rb_y(MASKS{i}), SZ(i), COLS{i}, 'filled', ...
            'MarkerEdgeColor','w','LineWidth',0.9,'DisplayName',LBL{i});
    end
end

axis(ax,'equal','tight'); grid(ax,'on');
set(ax,'Color',[.04 .04 .10],'GridColor',[.3 .3 .4], ...
       'XColor','w','YColor','w','FontSize',11);
title(ax,'Rebar Detection Map  (lag=17, log10+smooth)','Color','w','FontSize',14,'FontWeight','bold');
xlabel(ax,'X position (cm)','Color','w','FontSize',12);
ylabel(ax,'Y position (cm)','Color','w','FontSize',12);
legend(ax,'Location','northeastoutside','TextColor','w','Color',[.08 .08 .12],'FontSize',11);
hold(ax,'off');