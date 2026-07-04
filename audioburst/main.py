#!/usr/bin/env python3
import os
import sys
import time
import argparse
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from audioburst.config import Config, TXMode, RXMode, EncryptionMode
from audioburst.utils.logger import log
from audioburst.utils.config_loader import load_config, save_config
from audioburst.utils.helpers import ensure_dir, timestamp_str
from audioburst.tx.transmitter import Transmitter
from audioburst.rx.receiver import Receiver
from audioburst.crypto.keygen import generate_all_keys, display_key_info
from audioburst.modem.sampler import print_audio_devices

CONFIG_PATH=os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def clear_screen():
    os.system('clear' if os.name != 'nt' else 'cls')


def print_banner():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║         AudioBurst v3                                         ║
║  Secure High-Speed Acoustic Data Network By (c) J~Net 2026    ║
╚═══════════════════════════════════════════════════════════════╝
""")


def print_menu():
    print("""
  1) Send File
  2) Send Folder
  3) Send Text
  4) Receive (Live Audio)
  5) Receive from WAV File
  6) Generate Keys
  7) Config
  8) Mode Selection
  9) Audio Devices
 10) Exit
""")


def _check_encryption_warning(config: Config) -> bool:
    if config.crypto.mode == "none":
        print("\n  *** WARNING: Encryption is DISABLED (mode: none) ***")
        print("  *** Data will be transmitted as UNENCRYPTED plaintext! ***")
        print("  *** Anyone listening can read your data. ***\n")
        return True
    return False


def _confirm_or_skip(config: Config, prompt: str="Press Enter to start transmission...") -> None:
    if config.confirm_send:
        input(prompt)


def menu_send_file(config: Config):
    _check_encryption_warning(config)
    filepath=input("Enter file path: ").strip()
    if not filepath or not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return
    tx=Transmitter(config)
    print(f"\nTransmitting: {filepath}")
    print("Make sure receiver is listening...")
    _confirm_or_skip(config)
    tx.send_file(filepath)
    print("Transmission complete.")


def menu_send_folder(config: Config):
    _check_encryption_warning(config)
    folderpath=input("Enter folder path: ").strip()
    if not folderpath or not os.path.isdir(folderpath):
        print(f"Folder not found: {folderpath}")
        return
    tx=Transmitter(config)
    print(f"\nPacking and transmitting folder: {folderpath}")
    print("Make sure receiver is listening...")
    _confirm_or_skip(config)
    tx.send_file(folderpath)
    print("Transmission complete.")


def menu_send_text(config: Config):
    _check_encryption_warning(config)
    text=input("Enter text message: ").strip()
    if not text:
        print("No text entered.")
        return
    tx=Transmitter(config)
    print("\nTransmitting text message...")
    print("Make sure receiver is listening...")
    _confirm_or_skip(config)
    tx.send_text(text)
    print("Transmission complete.")


def menu_receive(config: Config):
    output_dir=config.paths.received_dir
    ensure_dir(output_dir)
    timeout_str=input("Enter listen timeout in seconds (default 30): ").strip()
    try:
        timeout=float(timeout_str) if timeout_str else 30.0
    except ValueError:
        timeout=30.0
    rx=Receiver(config)
    print(f"\nListening for {timeout}s... (output: {output_dir})")
    result=rx.receive_and_save(output_dir, timeout)
    if result:
        print(f"Received and saved to: {result}")
    else:
        print("No data received.")


def menu_receive_wav(config: Config):
    wav_path=input("Enter WAV file path: ").strip()
    if not wav_path or not os.path.isfile(wav_path):
        print(f"WAV file not found: {wav_path}")
        return
    output_dir=config.paths.received_dir
    ensure_dir(output_dir)
    rx=Receiver(config)
    print(f"\nDecoding WAV: {wav_path}")
    print(f"Output directory: {output_dir}")
    result=rx.receive_from_wav(wav_path, output_dir)
    if result:
        print(f"Decoded and saved to: {result}")
    else:
        print("Failed to decode data from WAV file.")


def menu_generate_keys(config: Config):
    keys_dir=config.paths.keys_dir
    print(f"\nGenerating keys in: {keys_dir}")
    results=generate_all_keys(keys_dir)
    print("\nKeys generated:")
    for key_type, info in results.items():
        if 'fingerprint' in info:
            print(f"  {key_type}: {info['path']} (fp: {info['fingerprint']})")
        elif 'size' in info:
            print(f"  {key_type}: {info['path']} ({info['size']} bytes)")
        else:
            print(f"  {key_type}: {info['path']}")
    display_key_info(keys_dir)


def _menu_encryption(config: Config):
    while True:
        clear_screen()
        print_banner()
        print("=== Encryption Mode ===")
        print(f"  Current: {config.crypto.mode}")
        print("""
  0) None        (no encryption)
  1) PSK         (AES-256-GCM pre-shared key)
  2) Public Key  (RSA-4096 hybrid)
  3) OTP         (one-time pad)
  4) Back
""")
        choice=input("Select encryption mode: ").strip()
        if choice == '0':
            config.crypto.mode="none"
            print("Encryption set to: none")
        elif choice == '1':
            config.crypto.mode="psk"
            print("Encryption set to: psk")
        elif choice == '2':
            config.crypto.mode="public_key"
            print("Encryption set to: public_key")
        elif choice == '3':
            config.crypto.mode="otp"
            print("Encryption set to: otp")
        elif choice == '4':
            return
        else:
            continue
        input("Press Enter...")


def menu_config(config: Config):
    while True:
        clear_screen()
        print_banner()
        print("=== Configuration ===")
        print(f"""
  1) Sample Rate:        {config.audio.sample_rate} Hz
  2) Tones:              {config.audio.tones}
  3) Symbol Rate:        {config.audio.symbol_rate} Hz
  4) Base Frequency:     {config.audio.base_freq} Hz
  5) Tone Spacing:       {config.audio.tone_spacing} Hz
  6) Amplitude:          {config.audio.amplitude}
  7) Bits per Tone:      {config.audio.bits_per_tone}
  8) Max Payload Size:   {config.packet.max_payload_size}
  9) FEC Redundancy:     {config.fec.redundancy}
 10) Encryption Mode:    {config.crypto.mode}
 11) Compression:        {config.compression}
 12) Save TX to WAV:     {config.save_to_wav}
 13) Saved WAV Dir:      {config.paths.saved_dir}
 14) Mute Sound:         {config.mute_sound}
 15) Confirm Send:       {config.confirm_send}
 16) Debug Mode:         {config.debug.enabled}
 17) Save Config
 18) Back
""")
        choice=input("Select option: ").strip()
        if choice == '1':
            val=input("Sample rate (44100/48000/96000): ").strip()
            if val:
                config.audio.sample_rate=int(val)
        elif choice == '2':
            val=input("Number of tones (8/16/32/64): ").strip()
            if val:
                config.audio.tones=int(val)
        elif choice == '3':
            val=input("Symbol rate: ").strip()
            if val:
                config.audio.symbol_rate=float(val)
                config.audio.symbol_duration=1.0 / float(val)
        elif choice == '4':
            val=input("Base frequency (Hz): ").strip()
            if val:
                config.audio.base_freq=float(val)
        elif choice == '5':
            val=input("Tone spacing (Hz): ").strip()
            if val:
                config.audio.tone_spacing=float(val)
        elif choice == '6':
            val=input("Amplitude (0.0-1.0): ").strip()
            if val:
                config.audio.amplitude=float(val)
        elif choice == '7':
            val=input("Bits per tone (1/2/4): ").strip()
            if val:
                config.audio.bits_per_tone=int(val)
        elif choice == '8':
            val=input("Max payload size: ").strip()
            if val:
                config.packet.max_payload_size=int(val)
        elif choice == '9':
            val=input("FEC redundancy (0.1-0.5): ").strip()
            if val:
                config.fec.redundancy=float(val)
        elif choice == '10':
            _menu_encryption(config)
        elif choice == '11':
            val=input("Enable compression? (y/n): ").strip().lower()
            config.compression=val == 'y'
        elif choice == '12':
            val=input("Save TX audio to WAV file? (y/n): ").strip().lower()
            config.save_to_wav=val == 'y'
        elif choice == '13':
            val=input(f"Saved WAV directory [{config.paths.saved_dir}]: ").strip()
            if val:
                config.paths.saved_dir=val
        elif choice == '14':
            val=input("Mute audio playback? (y/n): ").strip().lower()
            config.mute_sound=val == 'y'
        elif choice == '15':
            val=input("Require Enter confirmation before send? (y/n): ").strip().lower()
            config.confirm_send=val == 'y'
        elif choice == '16':
            val=input("Enable debug? (y/n): ").strip().lower()
            config.debug.enabled=val == 'y'
        elif choice == '17':
            save_config(config, CONFIG_PATH)
            print(f"Config saved to {CONFIG_PATH}")
            input("Press Enter...")
        elif choice == '18':
            return


def menu_mode_selection(config: Config):
    while True:
        clear_screen()
        print_banner()
        print("=== Mode Selection ===")
        print(f"  Current TX Mode: {config.tx_mode}")
        print(f"  Current RX Mode: {config.rx_mode}")
        print(f"  Encryption:      {config.crypto.mode}")
        print("""
  1) FAST      (max bitrate, low redundancy)
  2) BALANCED  (default)
  3) ROBUST    (high redundancy + FEC)
  4) STEALTH   (lower amplitude, slower)
  5) Back
""")
        choice=input("Select mode: ").strip()
        if choice == '1':
            config.apply_mode("fast")
            print("Mode set to FAST")
        elif choice == '2':
            config.apply_mode("balanced")
            print("Mode set to BALANCED")
        elif choice == '3':
            config.apply_mode("robust")
            print("Mode set to ROBUST")
        elif choice == '4':
            config.apply_mode("stealth")
            print("Mode set to STEALTH")
        elif choice == '5':
            return
        else:
            continue
        input("Press Enter...")


def menu_audio_devices():
    print_audio_devices()
    input("Press Enter...")


def main():
    parser=argparse.ArgumentParser(description="AudioBurst v3 - Secure High-Speed Acoustic Data Network")
    parser.add_argument('--config', type=str, default=CONFIG_PATH, help='Path to config file')
    parser.add_argument('--send', type=str, help='Send a file')
    parser.add_argument('--send-folder', type=str, help='Send a folder')
    parser.add_argument('--send-text', type=str, help='Send a text message')
    parser.add_argument('--receive', action='store_true', help='Receive mode (live audio)')
    parser.add_argument('--receive-wav', type=str, help='Receive/decode from a WAV file')
    parser.add_argument('--timeout', type=float, default=30.0, help='Receive timeout')
    parser.add_argument('--output', type=str, help='Output directory for received files')
    parser.add_argument('--mode', type=str, choices=['fast', 'balanced', 'robust', 'stealth'],
                        help='Transmission mode')
    parser.add_argument('--generate-keys', action='store_true', help='Generate encryption keys')
    parser.add_argument('--list-devices', action='store_true', help='List audio devices')
    parser.add_argument('--save-wav', action='store_true', default=None, help='Save TX audio to WAV file')
    parser.add_argument('--no-save-wav', action='store_false', dest='save_wav', help='Do not save TX audio to WAV')
    args=parser.parse_args()

    config=load_config(args.config) if os.path.exists(args.config) else Config()

    if args.mode:
        config.apply_mode(args.mode)

    if args.save_wav is not None:
        config.save_to_wav=args.save_wav

    if args.list_devices:
        print_audio_devices()
        return

    if args.generate_keys:
        generate_all_keys(config.paths.keys_dir)
        display_key_info(config.paths.keys_dir)
        return

    if args.send:
        _check_encryption_warning(config)
        tx=Transmitter(config)
        tx.send_file(args.send)
        return

    if args.send_folder:
        _check_encryption_warning(config)
        tx=Transmitter(config)
        tx.send_file(args.send_folder)
        return

    if args.send_text:
        _check_encryption_warning(config)
        tx=Transmitter(config)
        tx.send_text(args.send_text)
        return

    if args.receive:
        rx=Receiver(config)
        output_dir=args.output or config.paths.received_dir
        ensure_dir(output_dir)
        result=rx.receive_and_save(output_dir, args.timeout)
        if result:
            print(f"Received: {result}")
        else:
            print("No data received.")
        return

    if args.receive_wav:
        rx=Receiver(config)
        output_dir=args.output or config.paths.received_dir
        ensure_dir(output_dir)
        result=rx.receive_from_wav(args.receive_wav, output_dir)
        if result:
            print(f"Decoded from WAV: {result}")
        else:
            print("Failed to decode data from WAV file.")
        return

    if config.debug.enabled:
        log.setup_file_logging(config.debug.log_file, config.debug.log_level)

    while True:
        clear_screen()
        print_banner()
        print_menu()
        choice=input("Select option: ").strip()
        if choice == '1':
            menu_send_file(config)
        elif choice == '2':
            menu_send_folder(config)
        elif choice == '3':
            menu_send_text(config)
        elif choice == '4':
            menu_receive(config)
        elif choice == '5':
            menu_receive_wav(config)
        elif choice == '6':
            menu_generate_keys(config)
        elif choice == '7':
            menu_config(config)
        elif choice == '8':
            menu_mode_selection(config)
        elif choice == '9':
            menu_audio_devices()
        elif choice == '10':
            print("Exiting AudioBurst v3. Goodbye.")
            break
        else:
            print("Invalid option.")
        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
