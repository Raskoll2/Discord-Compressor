import sys
import os
import subprocess
import threading
import json
import tempfile
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QObject, Slot, Signal, Property, QUrl

CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0

class VideoCompressor(QObject):
    processingStarted = Signal()
    previewReady = Signal(str)
    exportFinished = Signal(str)
    errorOccurred = Signal(str)
    
    rawDurationChanged = Signal()
    startTimeChanged = Signal()
    endTimeChanged = Signal()
    availableFpsChanged = Signal()
    nativeSizeChanged = Signal()
    resolutionChanged = Signal()
    targetFpsChanged = Signal()
    encoderChanged = Signal()
    hwAccelChanged = Signal()

    def __init__(self):
        super().__init__()
        self._video_path = ""
        self._raw_duration = 1.0
        self._raw_bitrate = 0.0
        self._raw_framerate = 30.0
        self._raw_width = 1920.0
        self._scaled_native_bitrate_kbps = 0.0
        
        self._start_time = 0.0
        self._end_time = 1.0
        self._target_mb = 10.0
        self._resolution = 1920
        self._target_fps = 30.0
        self._available_fps = [30.0]
        self._native_size_est = 0.0
        
        self._encoder = "h264"
        self._hw_accel = "cpu"
        
        self._is_processing = False
        self._preview_counter = 0
        self._temp_dir = tempfile.gettempdir()

    def cleanup_temp_files(self):
        for i in range(3):
            f = os.path.join(self._temp_dir, f"discord_comp_preview_{i}.mp4")
            if os.path.exists(f):
                try: os.remove(f)
                except: pass
        for file in os.listdir(self._temp_dir):
            if file.startswith("ffmpeg2pass_log"):
                try: os.remove(os.path.join(self._temp_dir, file))
                except: pass

    @Property(float, notify=rawDurationChanged)
    def rawDuration(self): return self._raw_duration

    @Property(list, notify=availableFpsChanged)
    def availableFps(self): return self._available_fps

    @Property(float, notify=nativeSizeChanged)
    def nativeSizeEstimate(self): return self._native_size_est

    @Property(str)
    def videoPath(self): return self._video_path

    @videoPath.setter
    def videoPath(self, val): 
        url = QUrl(val)
        self._video_path = url.toLocalFile() if url.isLocalFile() else val
        self.cleanup_temp_files()
        self._extract_metadata()

    def _extract_metadata(self):
        try:
            cmd = ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", self._video_path]
            # ADDED stdin=subprocess.DEVNULL to prevent windowless crash
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, creationflags=CREATE_NO_WINDOW, stdin=subprocess.DEVNULL)
            data = json.loads(result.stdout)
            
            self._raw_duration = float(data.get('format', {}).get('duration', 60.0))
            self.rawDurationChanged.emit()
            
            self._start_time = 0.0
            self._end_time = self._raw_duration
            self.startTimeChanged.emit()
            self.endTimeChanged.emit()
            
            try:
                self._raw_bitrate = float(data['format']['bit_rate'])
            except KeyError:
                size = float(data['format']['size'])
                self._raw_bitrate = (size * 8) / self._raw_duration
                
            v_stream = next((s for s in data.get('streams', []) if s.get('codec_type') == 'video'), None)
            if v_stream:
                self._raw_width = float(v_stream.get('width', 1920))
                fps_str = v_stream.get('avg_frame_rate', v_stream.get('r_frame_rate', '30/1'))
                num, den = map(int, fps_str.split('/')) if '/' in fps_str else (float(fps_str), 1)
                self._raw_framerate = num / den if den != 0 else 30.0
                
            fps_list = [round(self._raw_framerate, 2)]
            for f in [60, 50, 30, 24, 15]:
                if f <= fps_list[0] - 0.5: fps_list.append(float(f))
            self._available_fps = fps_list
            self._target_fps = fps_list[0]
            self.availableFpsChanged.emit()
            self.targetFpsChanged.emit()
            self._update_size_estimate()
        except Exception:
            self.errorOccurred.emit("Could not read video file.")

    def _update_size_estimate(self):
        duration = max(0.1, self._end_time - self._start_time)
        base_bytes = (self._raw_bitrate / 8) * duration
        res_ratio = (self._resolution / max(self._raw_width, 1.0)) ** 1.5
        fps_ratio = self._target_fps / max(self._raw_framerate, 1.0)
        scaled_bytes = base_bytes * res_ratio * fps_ratio
        self._scaled_native_bitrate_kbps = (scaled_bytes * 8) / duration / 1000
        self._native_size_est = scaled_bytes / (1024 * 1024)
        self.nativeSizeChanged.emit()

    @Property(float, notify=startTimeChanged)
    def startTime(self): return self._start_time
    @startTime.setter
    def startTime(self, val): 
        self._start_time = val
        self.startTimeChanged.emit()
        self._update_size_estimate()

    @Property(float, notify=endTimeChanged)
    def endTime(self): return self._end_time
    @endTime.setter
    def endTime(self, val): 
        self._end_time = val
        self.endTimeChanged.emit()
        self._update_size_estimate()

    @Property(float, notify=targetFpsChanged)
    def targetFps(self): return self._target_fps
    @targetFps.setter
    def targetFps(self, val): 
        self._target_fps = val
        self.targetFpsChanged.emit()
        self._update_size_estimate()

    @Property(int, notify=resolutionChanged)
    def resolution(self): return self._resolution
    @resolution.setter
    def resolution(self, val): 
        self._resolution = val
        self.resolutionChanged.emit()
        self._update_size_estimate()

    @Property(float)
    def targetMb(self): return self._target_mb
    @targetMb.setter
    def targetMb(self, val): self._target_mb = val

    @Property(str, notify=encoderChanged)
    def encoder(self): return self._encoder
    @encoder.setter
    def encoder(self, val): 
        self._encoder = val
        self.encoderChanged.emit()

    @Property(str, notify=hwAccelChanged)
    def hwAccel(self): return self._hw_accel
    @hwAccel.setter
    def hwAccel(self, val): 
        self._hw_accel = val
        self.hwAccelChanged.emit()

    @Slot()
    def generatePreview(self):
        if self._video_path and not self._is_processing:
            self.processingStarted.emit()
            threading.Thread(target=self._run_preview_encode, daemon=True).start()

    def _run_preview_encode(self):
        self._is_processing = True
        try:
            self._preview_counter += 1
            preview_file = os.path.join(self._temp_dir, f"discord_comp_preview_{self._preview_counter % 3}.mp4")
            # ADDED -nostdin flag
            cmd = ["ffmpeg", "-nostdin", "-y", "-i", self._video_path, "-ss", str(self._start_time), "-to", str(self._end_time),
                   "-vf", f"scale={self._resolution}:-2", "-r", str(self._target_fps),
                   "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28", "-c:a", "aac", "-b:a", "128k", preview_file]
            # ADDED stdin=subprocess.DEVNULL
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, creationflags=CREATE_NO_WINDOW, stdin=subprocess.DEVNULL)
            if res.returncode == 0: self.previewReady.emit(QUrl.fromLocalFile(preview_file).toString())
            else: self.errorOccurred.emit("Preview encode failed.")
        except Exception: self.errorOccurred.emit("System error during preview.")
        finally: self._is_processing = False

    @Slot(str)
    def exportVideo(self, out_path_url):
        if self._video_path and not self._is_processing:
            url = QUrl(out_path_url)
            out_path = url.toLocalFile() if url.isLocalFile() else out_path_url
            self.processingStarted.emit()
            threading.Thread(target=self._run_final_encode, args=(out_path,), daemon=True).start()

    def _run_final_encode(self, out_path):
        self._is_processing = True
        try:
            duration = max(0.1, self._end_time - self._start_time)
            target_kbps = min((self._target_mb * 8192) / duration, self._scaled_native_bitrate_kbps * 1.1)
            v_kbps = max(100, int(target_kbps - 128))
            v_codec, v_flags, a_codec, is_hw = "libx264", ["-preset", "fast"], "aac", False
            
            if self._encoder == "h264":
                if self._hw_accel == "nvenc": v_codec, v_flags, is_hw = "h264_nvenc", ["-preset", "p4"], True
                elif self._hw_accel == "amf": v_codec, v_flags, is_hw = "h264_amf", ["-usage", "lowlatency"], True
                elif self._hw_accel == "qsv": v_codec, v_flags, is_hw = "h264_qsv", ["-preset", "faster"], True
            elif self._encoder == "h265":
                if self._hw_accel == "nvenc": v_codec, v_flags, is_hw = "hevc_nvenc", ["-preset", "p4", "-tag:v", "hvc1"], True
                elif self._hw_accel == "amf": v_codec, v_flags, is_hw = "hevc_amf", ["-usage", "lowlatency", "-tag:v", "hvc1"], True
                elif self._hw_accel == "qsv": v_codec, v_flags, is_hw = "hevc_qsv", ["-preset", "faster", "-tag:v", "hvc1"], True
                else: v_codec, v_flags = "libx265", ["-preset", "fast", "-tag:v", "hvc1"]
            elif self._encoder == "vp9":
                v_codec, v_flags, a_codec = "libvpx-vp9", ["-row-mt", "1", "-cpu-used", "2"], "libopus"
                base, _ = os.path.splitext(out_path)
                out_path = base + ".webm"

            if is_hw:
                # ADDED -nostdin
                cmd = ["ffmpeg", "-nostdin", "-y", "-i", self._video_path, "-ss", str(self._start_time), "-to", str(self._end_time),
                       "-vf", f"scale={self._resolution}:-2", "-r", str(self._target_fps), "-c:v", v_codec, *v_flags, 
                       "-b:v", f"{v_kbps}k", "-maxrate", f"{v_kbps}k", "-bufsize", f"{v_kbps*2}k", "-c:a", a_codec, "-b:a", "128k", out_path]
                # ADDED stdin=subprocess.DEVNULL
                res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, creationflags=CREATE_NO_WINDOW, stdin=subprocess.DEVNULL)
                if res.returncode != 0: self.errorOccurred.emit("HW Encoder failed.")
                else: self.exportFinished.emit(out_path)
            else:
                log = os.path.join(self._temp_dir, "ffmpeg2pass_log")
                # ADDED -nostdin to pass 1 and 2
                p1 = ["ffmpeg", "-nostdin", "-y", "-i", self._video_path, "-ss", str(self._start_time), "-to", str(self._end_time),
                      "-vf", f"scale={self._resolution}:-2", "-r", str(self._target_fps), "-c:v", v_codec, *v_flags, 
                      "-b:v", f"{v_kbps}k", "-pass", "1", "-passlogfile", log, "-an", "-f", "null", "-"]
                p2 = ["ffmpeg", "-nostdin", "-y", "-i", self._video_path, "-ss", str(self._start_time), "-to", str(self._end_time),
                      "-vf", f"scale={self._resolution}:-2", "-r", str(self._target_fps), "-c:v", v_codec, *v_flags, 
                      "-b:v", f"{v_kbps}k", "-pass", "2", "-passlogfile", log, "-c:a", a_codec, "-b:a", "128k", out_path]
                
                # ADDED stdin=subprocess.DEVNULL
                if subprocess.run(p1, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW, stdin=subprocess.DEVNULL).returncode == 0 and \
                   subprocess.run(p2, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW, stdin=subprocess.DEVNULL).returncode == 0:
                    self.exportFinished.emit(out_path)
                else: self.errorOccurred.emit("Export failed.")
            self.cleanup_temp_files()
        except Exception: self.errorOccurred.emit("Critical export failure.")
        finally: self._is_processing = False

if __name__ == "__main__":
    args = sys.argv[1:]
    
    if "--headless" in args:
        args.remove("--headless")
        if args and os.path.exists(args[0]):
            c = VideoCompressor()
            c.videoPath = args[0]
            base, _ = os.path.splitext(args[0])
            out = f"{base}_comp{('.webm' if c.encoder == 'vp9' else '.mp4')}"
            c._run_final_encode(out)
            if os.name == 'nt':
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, f"Saved:\n{os.path.basename(out)}", "Discord Compressor", 0x40)
        sys.exit(0)
        
    else:
        app = QGuiApplication(sys.argv)
        engine = QQmlApplicationEngine()
        comp = VideoCompressor()
        app.aboutToQuit.connect(comp.cleanup_temp_files)
        
        engine.rootContext().setContextProperty("backend", comp)
        base = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        
        engine.load(QUrl.fromLocalFile(os.path.join(base, "main.qml")))
        if not engine.rootObjects():
            sys.exit(-1)
            
        if args and os.path.exists(args[0]):
            comp.videoPath = args[0]
            comp.generatePreview()
            
        sys.exit(app.exec())