import QtQuick
import qs.Ui

BarWidget {
    id: root
    moduleName: "versework.launcher"
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight

    WidgetButton {
        id: button
        anchors.fill: parent
        bar: root.bar
        text: "♫"
        tooltipText: "Versework"
        horizontalMargin: 7.5
        onPressed: function(button) {
            if (root.bar && button === Qt.LeftButton)
                root.bar.run("uwsm-app -- gtk-launch io.versework.Studio")
        }
    }
}
