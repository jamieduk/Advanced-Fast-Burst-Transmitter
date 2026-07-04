# AudioBurst v3 – Secure High-Speed Acoustic Data Network

## Super Fast Advanced Burst Transmitter

A modular Python framework designed to implement a high-speed, secure, resilient audio-based data transmission system without relying on GNU Radio, minimodem or any external modem applications.

The goal of this project is to create a software-defined acoustic packet radio network capable of securely transmitting files, folders and text over standard audio devices using parallel multi-tone modulation, forward error correction and modern cryptography.

---

## Project Location

```
/home/jay/Documents/Scripts/AI/OpenCode/Super-Fast-Advanced-Burst-Transmitter/
```

---

# Project Goals

The framework is designed to provide:

- High-speed acoustic data transfer
- Multi-tone parallel transmission
- Strong authenticated encryption
- Public key support
- Optional One-Time Pad mode
- Forward Error Correction
- CRC validation
- Automatic packet ordering
- Folder transfer support
- Modular Python architecture
- Linux compatibility
- Fully configurable operation
- Command line interface

---

# Features

## Transmission

- Single file transfer
- Entire folder transfer
- Text message transmission
- Automatic file reconstruction
- Original filenames preserved
- Original extensions preserved
- Original directory structure preserved

---

## Security

Supports multiple encryption modes.

### PSK Mode

- AES-256-GCM
- PBKDF2 or Argon2 key derivation
- Authentication tag verification

### Public Key Mode

Hybrid encryption.

- RSA or ECC
- Random AES session key
- Session key encrypted using public key
- Payload encrypted using AES-GCM

### Optional OTP Mode

- True One-Time Pad
- Key length validation
- Key reuse detection
- Warning system

---

## Reliability

Each packet includes:

- Session ID
- Sequence number
- Total packet count
- Payload length
- CRC32
- Packet markers

Features include:

- Automatic packet ordering
- Duplicate detection
- Missing packet recovery
- Reed-Solomon FEC
- Future retransmission support

---

# Modulation

AudioBurst v3 uses a custom multi-tone modulation engine.

Instead of sending a single tone at a time, multiple sine waves are transmitted simultaneously.

Configurable options include:

- 8 tones
- 16 tones
- 32 tones
- 64 tones

Receiver performs FFT-based frequency analysis for tone detection.

This architecture is designed to significantly exceed traditional single-channel acoustic modem throughput where channel conditions allow.

---

# Compression

Before encryption the payload may optionally be compressed.

Supported algorithms include:

- gzip
- zstd (future)

Compression occurs before encryption to maximise efficiency.

---

# Packet Format

Every transmitted frame follows the protocol:

```
[PREAMBLE]
[SYNC HEADER]
[SESSION ID]
[SEQ ID]
[TOTAL PACKETS]
[ENC TYPE]
[PAYLOAD LENGTH]
[PAYLOAD]
[CRC32]
[END MARKER]
```

---

# Operating Modes

## FAST

- Maximum throughput
- Low redundancy
- Minimal FEC

Suitable for:

- Clean wired audio
- Short distance

---

## BALANCED

- Moderate redundancy
- Recommended default

Suitable for:

- General operation

---

## ROBUST

- Heavy FEC
- Larger redundancy
- Maximum recovery

Suitable for:

- Noisy channels
- Weak signals

---

## STEALTH

- Lower amplitude
- Reduced bandwidth
- Slower transmission

Suitable for:

- Quiet environments
- Reduced detectability

---

# Configuration

Configuration is centralised in:

```
config.py
```

Includes settings for:

- Sample rate
- Number of tones
- Symbol rate
- Packet size
- Encryption mode
- Default keys
- FEC percentage
- Output directories
- Debug mode
- Audio devices

---

# Project Structure

```
audioburst/

├── main.py
├── config.py
│
├── tx/
│   ├── transmitter.py
│   ├── encoder.py
│   ├── file_loader.py
│
├── rx/
│   ├── receiver.py
│   ├── decoder.py
│   ├── sync.py
│
├── modem/
│   ├── multitone.py
│   ├── demod.py
│   ├── sampler.py
│
├── crypto/
│   ├── aes.py
│   ├── rsa.py
│   ├── otp.py
│   ├── keygen.py
│
├── fec/
│   ├── reedsolomon.py
│   ├── crc.py
│
├── protocol/
│   ├── frame.py
│   ├── serializer.py
│   ├── session.py
│
├── utils/
│   ├── logger.py
│   ├── config_loader.py
│   ├── helpers.py
```

---

# CLI

```
AudioBurst v3
=============

1) Send File
2) Send Folder
3) Send Text
4) Receive
5) Generate Keys
6) Config
7) Mode Selection
8) Exit
```

---

# Key Management

The framework includes tools for:

- Generate AES keys
- Generate RSA keypairs
- Generate ECC keypairs
- Import keys
- Export keys
- Fingerprint display
- Key validation

---

# Performance Design

Optimised for modern CPUs using:

- NumPy vector operations
- FFT processing
- Streaming pipelines
- Minimal Python loops
- Optional multiprocessing
- Memory-efficient buffering

---

# Security Design

AudioBurst follows several security principles.

- No plaintext payload logging
- No unnecessary key retention
- Secure authenticated encryption
- CRC validation
- Optional secure memory wiping
- Cryptographic correctness prioritised over speed

---

# Test Utilities

Development tools include:

- Test tone generator
- Noise simulator
- Packet loss simulator
- Decoder validator
- FEC testing
- Throughput benchmarking

---

# Planned Future Features

The modular architecture allows future expansion including:

- True OFDM implementation
- SDR support
- RF bridge
- Network tunnelling
- UDP fallback
- Adaptive bitrate
- Automatic frequency hopping
- Channel estimation
- Synchronisation improvements
- Live throughput graphs

---

# Dependencies

Minimum requirements:

- Python 3.11+
- NumPy
- SciPy

Recommended:

- cryptography
- reedsolo
- argon2-cffi
- pycryptodome

---

# Platform

Supported operating systems:

- Linux (Primary)

Future compatibility:

- Windows
- macOS

---

# Design Philosophy

AudioBurst v3 is intended to function as a fully software-defined acoustic packet radio system built entirely in Python.

Every subsystem is isolated into its own module to simplify maintenance, testing and future upgrades while keeping the codebase clean and extensible.

---

# License

Project licence to be determined by the project owner.

---

**Status:** Initial project specification and architecture complete. Development of individual modules is intended to proceed incrementally while preserving the modular design described above.
