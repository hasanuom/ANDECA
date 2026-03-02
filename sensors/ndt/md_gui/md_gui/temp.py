for k in range(self.nharmonics):
    # Input PCA-ed data
    if self.use_pca:
        self.processed_data_queue[k, :] = [self.transformed_data_queue[k, :],
                                           self.transformed_data_queue[k + self.nharmonics, :]]
    # Input Raw Data
    else:
        if self.use_reim:
            self.processed_data_queue[k, :] = np.real(self.raw_complex_data_queue[k, :])
            self.processed_data_queue[k + self.nharmonics, :] = np.imag(self.raw_complex_data_queue[k, :])
        else:
            self.processed_data_queue[k, :] = np.abs(self.raw_complex_data_queue[k, :])
            self.processed_data_queue[k + self.nharmonics, :] = np.degrees(np.angle(self.raw_complex_data_queue[k, :]))


    if self.use_detrend:
        self.processed_data_queue[k, :] = scipy.signal.detrend(self.processed_data_queue[k, :])
        self.processed_data_queue[k + self.nharmonics, :] = scipy.signal.detrend(self.processed_data_queue[k + self.nharmonics, :])

    if self.use_filter:
        self.processed_data_queue[k, :] = self.filter.apply_filter(self.processed_data_queue[k, :])
        self.processed_data_queue[k + self.nharmonics, :] = self.filter.apply_filter(self.processed_data_queue[k + self.nharmonics, :])

    if self.use_standard_normal:
        self.processed_data_queue[k, :] = self.standardise(self.processed_data_queue[k, :])
        self.processed_data_queue[k + self.nharmonics, :] = self.standardise(self.processed_data_queue[k + self.nharmonics, :])

    if self.use_fft:
        if self.cepstrum_input_ctrl[0].isChecked():
            self.processed_data_queue[k, :] = self.apply_fft(self.processed_data_queue[k, :])
            self.processed_data_queue[k + self.nharmonics, :] = self.apply_fft(self.processed_data_queue[k, :])
        else:
            self.processed_data_queue[k, :] = self.apply_fft(self.processed_data_queue[k + self.nharmonics, :])
            self.processed_data_queue[k + self.nharmonics, :] = self.apply_fft(self.processed_data_queue[k + self.nharmonics, :])

    if self.use_cepstrum:
        if self.cepstrum_input_ctrl[0].isChecked():
            self.processed_data_queue[k, :] = self.apply_cepstrum(self.processed_data_queue[k, :])
            self.processed_data_queue[k + self.nharmonics, :] = self.apply_cepstrum(self.processed_data_queue[k, :])
        else:
            self.processed_data_queue[k, :] = self.apply_fft(self.processed_data_queue[k + self.nharmonics, :])
            self.processed_data_queue[k + self.nharmonics, :] = self.apply_fft(self.processed_data_queue[k + self.nharmonics, :])

    if self.use_difference:
        self.processed_data_queue[k, :] = self.apply_differencing(self.processed_data_queue[k, :])
        self.processed_data_queue[k + self.nharmonics, :] = self.apply_differencing(self.processed_data_queue[k + self.nharmonics, :])


    if self.use_freq_diff:
        self.processed_data_queue[k, :] = self.freq_differencing(self.processed_data_queue[k, :], k)

    if self.use_harmonic_removal:
        self.processed_data_queue[k, :] = self.apply_harmonic_removal()

# if self.use_fft_2d:
#     z = self.processed_data_queue[k, :] + 1j * self.processed_data_queue[k + self.nharmonics, :]
#     self.processed_data_queue[k, :] = self.apply_2d_fft()

# Choose the harmonic to plot
for m, mask in enumerate(self.harmonic_mask):
    if mask:
        if self.use_reim:
            self.image_data[0] = np.real(self.processed_data_queue[m, :])
            self.image_data[1] = np.imag(self.processed_data_queue[m + self.nharmonics, :])
            else:
            self.image_data[0] = np.abs(self.processed_data_queue[m, :])
            self.image_data[1] = np.angle(self.processed_data_queue[m, :])
