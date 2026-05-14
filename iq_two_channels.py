import numpy as np
from bladerf import _bladerf

def make_tone(freq, sample_rate, n, amp=1):
    """Generate a complex tone at given baseband freq (Hz)."""
    t = np.arange(n) / sample_rate
    return amp * np.exp(1j * 2 * np.pi * freq * t).astype(np.complex64)

def interleave_ch(ch0, ch1):
    """
    Interleave two complex arrays into a single buffer for dual‑TX streaming.
    Many SDR APIs expect channel‑interleaved I0,Q0, I1,Q1, I0,Q0, I1,Q1, ...
    """
    # ch0, ch1 are complex64 arrays of same length
    # view as int16 (I = real*scale, Q = imag*scale)
    # but here we keep float for conceptual clarity
    # For bladeRF, format is SC16 (i.e. int16), so conversion required later
    N = len(ch0)
    out = np.zeros(2 * N, dtype=np.complex64)
    out[0::2] = ch0
    out[1::2] = ch1
    return out

def complex_to_sc16_iqbuf(cbuf, scale=2048):
    """
    Convert complex64 buffer into interleaved int16 IQ (I, Q) sequence,
    as required by SC16_Q11 format for bladeRF.
    Returns a bytes object.
    """
    # clip to [-1, +1] then scale
    re = np.clip(cbuf.real, -1, 1) * scale
    im = np.clip(cbuf.imag, -1, 1) * scale
    # convert to int16
    i16 = np.empty((len(cbuf)*2,), dtype=np.int16)
    i16[0::2] = re.astype(np.int16)
    i16[1::2] = im.astype(np.int16)
    return i16.tobytes()

def two_tx_example():
    sdr = _bladerf.BladeRF()

    # Configure TX channels
    tx0 = sdr.Channel(_bladerf.CHANNEL_TX(0))
    tx1 = sdr.Channel(_bladerf.CHANNEL_TX(1))

    sample_rate = 10e6
    center_freq = 200e6
    # sample_rate = 20e6
    #center_freq = 2.4e9
    gain = 10  # start low

    # set up both TX channels
    for tx in (tx0, tx1):
        tx.frequency = center_freq
        tx.sample_rate = sample_rate
        tx.bandwidth = sample_rate / 2
        tx.gain = gain

    # configure synchronous dual‑channel TX stream
    sdr.sync_config(
        layout=_bladerf.ChannelLayout.TX_X2,
        fmt=_bladerf.Format.SC16_Q11,
        num_buffers=16,
        buffer_size=8192,
        num_transfers=8,
        stream_timeout=3500,
    )

    # generate two tones (at two different baseband offsets)
    N = 8192  # samples per buffer
    # tone0 = make_tone(100e6, sample_rate, N)  # +100 kHz offset
    # tone1 = make_tone(-200e6, sample_rate, N)  # –200 kHz offset
    tone0 = make_tone(100e3, sample_rate, N)  # +100 kHz offset
    tone1 = make_tone(-200e3, sample_rate, N)  # –200 kHz offset

    # interleave channels
    inter = interleave_ch(tone0, tone1)
    buf = complex_to_sc16_iqbuf(inter)

    # enable
    tx0.enable = True
    tx1.enable = True

    # transmit for some number of buffers
    for _ in range(5 * 1000):
        sdr.sync_tx(buf, N)  # N = number of complex “frames” per channel

    # disable
    tx0.enable = False
    tx1.enable = False

    i_samples = np.real(inter)
    q_samples = np.imag(inter)
    iq_csv_data = np.column_stack((i_samples, q_samples))  # Shape: (N, 2)

    np.savetxt('iq_two_channels_out.csv', iq_csv_data, delimiter=',', header='I,Q', comments='', fmt='%.6f')


if __name__ == "__main__":
    two_tx_example()
