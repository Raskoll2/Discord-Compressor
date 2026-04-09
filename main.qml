import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Dialogs
import QtMultimedia

ApplicationWindow {
    visible: true
    width: 1400
    height: 900
    title: "Discord Compressor"

    Material.theme: Material.Dark
    Material.accent: Material.DeepPurple

    Connections {
        target: backend
        function onPreviewReady(previewUrl) {
            videoPlayer.source = previewUrl
            videoPlayer.play()
            statusText.text = "Preview updated."
        }
        function onExportFinished(outPath) {
            statusText.text = "Saved successfully to " + outPath
        }
        function onErrorOccurred(msg) {
            statusText.text = "Error: " + msg
        }
        function onProcessingStarted() {
            statusText.text = "Processing..."
        }
    }

    FileDialog {
        id: openDialog
        title: "Select Video"
        nameFilters: ["Video Files (*.mp4 *.mkv *.mov *.webm)"]
        onAccepted: {
            backend.videoPath = selectedFile
            statusText.text = "Loaded video. Set trims and click 'Update Preview'."
        }
    }

    FileDialog {
        id: saveDialog
        title: "Save Compressed Video"
        fileMode: FileDialog.SaveFile
        nameFilters: ["Video Files (*.mp4 *.webm)"]
        defaultSuffix: "mp4"
        onAccepted: {
            backend.exportVideo(selectedFile)
        }
    }

    SplitView {
        anchors.fill: parent
        anchors.margins: 15

        // LEFT PANE: Controls
        Rectangle {
            SplitView.preferredWidth: 350
            SplitView.minimumWidth: 300
            SplitView.maximumWidth: 450
            color: "transparent"

            ColumnLayout {
                anchors.fill: parent
                spacing: 20

                Button {
                    text: "Load Video"
                    Layout.fillWidth: true
                    font.bold: true
                    onClicked: openDialog.open()
                }

                GroupBox {
                    title: "Trim (Seconds)"
                    Layout.fillWidth: true
                    
                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: "Start:"; Layout.fillWidth: true }
                            TextField {
                                // Dynamic binding to backend, formatting to 2 decimals
                                text: Number(backend.startTime).toFixed(2)
                                validator: DoubleValidator { bottom: 0 }
                                Layout.preferredWidth: 80
                                onEditingFinished: backend.startTime = parseFloat(text) || 0
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: "End:"; Layout.fillWidth: true }
                            TextField {
                                text: Number(backend.endTime).toFixed(2)
                                validator: DoubleValidator { bottom: 0 }
                                Layout.preferredWidth: 80
                                onEditingFinished: backend.endTime = parseFloat(text) || 0
                            }
                        }
                    }
                }

                GroupBox {
                    title: "Output Settings"
                    Layout.fillWidth: true

                    ColumnLayout {
                        anchors.fill: parent
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: "Encoder:"; Layout.fillWidth: true }
                            ComboBox {
                                id: encoderCombo
                                Layout.preferredWidth: 160
                                model: ["H.264 (Standard)", "H.265 (HEVC)", "VP9 (WebM)"]
                                onActivated: {
                                    if (currentIndex === 0) backend.encoder = "h264"
                                    else if (currentIndex === 1) backend.encoder = "h265"
                                    else if (currentIndex === 2) backend.encoder = "vp9"
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: "HW Accel:"; Layout.fillWidth: true }
                            ComboBox {
                                id: hwCombo
                                Layout.preferredWidth: 160
                                model: ["CPU (Software)", "NVIDIA (NVENC)", "AMD (AMF)", "Intel (QSV)"]
                                onActivated: {
                                    if (currentIndex === 0) backend.hwAccel = "cpu"
                                    else if (currentIndex === 1) backend.hwAccel = "nvenc"
                                    else if (currentIndex === 2) backend.hwAccel = "amf"
                                    else if (currentIndex === 3) backend.hwAccel = "qsv"
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: "Resolution:"; Layout.fillWidth: true }
                            ComboBox {
                                id: resCombo
                                Layout.preferredWidth: 160
                                model: ["1080p", "1440p", "720p", "480p"]
                                onActivated: {
                                    if (currentText === "1080p") backend.resolution = 1920
                                    else if (currentText === "1440p") backend.resolution = 2560
                                    else if (currentText === "720p") backend.resolution = 1280
                                    else if (currentText === "480p") backend.resolution = 848
                                }
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: "Framerate:"; Layout.fillWidth: true }
                            ComboBox {
                                id: fpsCombo
                                Layout.preferredWidth: 160
                                model: backend.availableFps
                                onModelChanged: currentIndex = 0
                                onActivated: backend.targetFps = model[currentIndex]
                            }
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: "Target Size (MB):"; Layout.fillWidth: true }
                            TextField {
                                text: "10"
                                validator: DoubleValidator { bottom: 1; top: 500 }
                                Layout.preferredWidth: 80
                                onTextChanged: backend.targetMb = parseFloat(text) || 10
                            }
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                Button {
                    text: "Update Preview"
                    Layout.fillWidth: true
                    onClicked: backend.generatePreview()
                }

                Button {
                    text: "Save Final"
                    Layout.fillWidth: true
                    font.bold: true
                    Material.background: Material.DeepPurple
                    Material.foreground: "white"
                    onClicked: saveDialog.open()
                }

                Rectangle {
                    Layout.fillWidth: true
                    height: 40
                    color: "#2a2a38"
                    radius: 4
                    Label {
                        id: statusText
                        anchors.centerIn: parent
                        text: "Ready."
                        color: "#a6adc8"
                    }
                }
            }
        }

        // RIGHT PANE: Preview Player & Progress Bar
        Rectangle {
            SplitView.fillWidth: true
            color: "#11111b"
            radius: 8
            border.color: "#2a2a38"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 10

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    MediaPlayer {
                        id: videoPlayer
                        audioOutput: AudioOutput {}
                        videoOutput: videoOut
                    }

                    VideoOutput {
                        id: videoOut
                        anchors.fill: parent
                        fillMode: VideoOutput.PreserveAspectFit
                    }

                    Rectangle {
                        anchors.top: parent.top
                        anchors.right: parent.right
                        anchors.margins: 15
                        width: sizeLabel.width + 20
                        height: 30
                        color: "#80000000"
                        radius: 15
                        visible: backend.nativeSizeEstimate > 0

                        Label {
                            id: sizeLabel
                            anchors.centerIn: parent
                            text: "Est. Native: " + backend.nativeSizeEstimate.toFixed(1) + " MB"
                            color: "white"
                            font.pixelSize: 12
                            font.bold: true
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            if (videoPlayer.playbackState === MediaPlayer.PlayingState) {
                                videoPlayer.pause()
                            } else {
                                videoPlayer.play()
                            }
                        }
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 30

                    Rectangle {
                        id: track
                        anchors.centerIn: parent
                        width: parent.width - 20
                        height: 6
                        color: "#313244"
                        radius: 3

                        // Highlighted area between the dots
                        Rectangle {
                            height: parent.height
                            color: Material.accent
                            radius: 3
                            x: (backend.startTime / Math.max(backend.rawDuration, 0.1)) * track.width
                            width: ((backend.endTime - backend.startTime) / Math.max(backend.rawDuration, 0.1)) * track.width
                        }

                        // Draggable Start Dot
                        Rectangle {
                            width: 16; height: 16; radius: 8; color: "white"
                            anchors.verticalCenter: parent.verticalCenter
                            x: (backend.startTime / Math.max(backend.rawDuration, 0.1)) * track.width - (width / 2)

                            MouseArea {
                                anchors.fill: parent
                                anchors.margins: -15 // Expands the hit target for easier grabbing
                                cursorShape: Qt.SizeHorCursor
                                onPositionChanged: (mouse) => {
                                    if (pressed) {
                                        let pt = mapToItem(track, mouse.x, mouse.y)
                                        let newTime = (pt.x / Math.max(track.width, 1)) * backend.rawDuration
                                        // Bound logic: cannot drag past 0, and cannot drag past the End dot minus a small buffer
                                        newTime = Math.max(0, Math.min(newTime, backend.endTime - 0.1))
                                        backend.startTime = parseFloat(newTime.toFixed(2))
                                    }
                                }
                            }
                        }

                        // Draggable End Dot
                        Rectangle {
                            width: 16; height: 16; radius: 8; color: "white"
                            anchors.verticalCenter: parent.verticalCenter
                            x: (backend.endTime / Math.max(backend.rawDuration, 0.1)) * track.width - (width / 2)

                            MouseArea {
                                anchors.fill: parent
                                anchors.margins: -15 // Expands the hit target for easier grabbing
                                cursorShape: Qt.SizeHorCursor
                                onPositionChanged: (mouse) => {
                                    if (pressed) {
                                        let pt = mapToItem(track, mouse.x, mouse.y)
                                        let newTime = (pt.x / Math.max(track.width, 1)) * backend.rawDuration
                                        // Bound logic: cannot drag past Start dot plus buffer, and cannot exceed raw duration
                                        newTime = Math.max(backend.startTime + 0.1, Math.min(newTime, backend.rawDuration))
                                        backend.endTime = parseFloat(newTime.toFixed(2))
                                    }
                                }
                            }
                        }

                        // Playhead indicator
                        Rectangle {
                            width: 4; height: 20; radius: 2; color: "#f38ba8"
                            anchors.verticalCenter: parent.verticalCenter
                            property real currentRawPos: backend.startTime + (videoPlayer.position / 1000.0)
                            x: (currentRawPos / Math.max(backend.rawDuration, 0.1)) * track.width - (width / 2)
                            visible: videoPlayer.position > 0
                        }
                    }
                }
            }
        }
    }
}