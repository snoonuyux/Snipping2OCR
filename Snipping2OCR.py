import io
import sys      #获取命令行参数
import numpy as np
import pyperclip    #copy and paste clipboard functions
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import *
import pytesseract
from PIL import Image   #read picture
from cnocr import CnOcr

try:
    from pynotifier import Notification     #displaying desktop notifications
except ImportError:
    pass


class LanguageSelect(QWidget):
    """ 选择识别语言方法
    """
    switch_window = QtCore.pyqtSignal(str)      #创建要传递的信号

    def __init__(self, parent=None):
        super(LanguageSelect, self).__init__(parent)
        self.initUI()

    def initUI(self):
        # 设置主窗口标题及图标
        self.setWindowTitle('Select OCR Language')
        self.setWindowIcon(QIcon('window_logo.ico'))

        # 水平布局
        layout = QHBoxLayout()
        self.setLayout(layout)

        #用来选择语言的radio button
        self.button1 = QRadioButton('中文或包含中英文')
        #self.button1.setChecked(True)
        self.button1.language = 'CN'
        self.button1.toggled.connect(self.buttonState)
        layout.addWidget(self.button1)

        self.button2 = QRadioButton('English or Number')
        self.button2.language = 'EN'
        self.button2.toggled.connect(self.buttonState)
        layout.addWidget(self.button2)

        #用来连接槽函数进行信号传递的push button
        self.button3 = QPushButton('Start Snipping')
        self.button3.setCheckable(True)
        self.button3.clicked.connect(self.switch)
        layout.addWidget(self.button3)

        #添加开始截屏快捷键
        self.shortcut = QShortcut(QKeySequence("Alt+Q"), self)
        self.shortcut.activated.connect(self.switch)
        self.shortcut.setEnabled(True)

        # 居中显示处理
        self.move_center()

    def move_center(self):
        screen = QDesktopWidget().screenGeometry()
        form = self.geometry()
        x_move_step = (screen.width() - form.width()) / 2
        y_move_step = (screen.height() - form.height()) / 2
        self.move(x_move_step, y_move_step)

    #确定所要传递的信号的槽函数
    def buttonState(self):
        radiobtn = self.sender()
        if radiobtn.text() == '中文或包含中英文':
            if radiobtn.isChecked():
                self.language = radiobtn.language
            else:
                self.language = 'na'

        if radiobtn.text() == 'English or Number':
            if radiobtn.isChecked():
                self.language = radiobtn.language
            else:
                self.language = 'na'

    # 在希望实现跳转界面的按钮上添加可以发射信号的槽函数
    def switch(self):
        self.switch_window.emit(self.language)


class Snipping(QWidget):
    """ 截屏方法
    """
    switch_window = QtCore.pyqtSignal()

    def __init__(self, text, parent=None, flags=Qt.WindowFlags()):
        super().__init__(parent=parent, flags=flags)

        self.setWindowTitle("TextShot")
        self.setWindowIcon(QIcon('window_logo.ico'))

        self.label = text

        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Dialog
        )
        self.setWindowState(self.windowState() | Qt.WindowFullScreen)

        self.screen = QtWidgets.QApplication.screenAt(QtGui.QCursor.pos()).grabWindow(0)
        palette = QtGui.QPalette()
        palette.setBrush(self.backgroundRole(), QtGui.QBrush(self.screen))
        self.setPalette(palette)

        QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.CrossCursor))

        self.start, self.end = QtCore.QPoint(), QtCore.QPoint()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            QtWidgets.QApplication.quit()

        return super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QtGui.QColor(0, 0, 0, 100))
        painter.drawRect(0, 0, self.width(), self.height())

        if self.start == self.end:
            return super().paintEvent(event)

        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), 3))
        painter.setBrush(painter.background())
        painter.drawRect(QtCore.QRect(self.start, self.end))
        return super().paintEvent(event)

    def mousePressEvent(self, event):
        self.start = self.end = event.pos()
        self.update()
        return super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.end = event.pos()
        self.update()
        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.start == self.end:
            return super().mouseReleaseEvent(event)

        self.hide()
        QtWidgets.QApplication.processEvents()
        shot = self.screen.copy(QtCore.QRect(self.start, self.end))

        if self.label == 'CN':
            print("a")
            getOCR(shot)
        elif self.label == 'EN':
            print("b")
            processImage(shot)
        elif self.label == 'na':
            print("c")
            getOCR(shot)

        #QtWidgets.QApplication.quit()
        QtWidgets.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))

        self.switch_window.connect(self.signalCall)
        self.switch_window.emit()

    def signalCall(self):
        print('Signal emit.')


class ContentShow(QMainWindow):
    """ 显示截屏内容方法
    """
    switch_window = QtCore.pyqtSignal()

    def __init__(self):
        super(ContentShow, self).__init__()
        self.__initUI__()

    def __initUI__(self):
        self.setMinimumSize(QSize(520, 320))
        self.setWindowTitle('Snipping2OCR Tool')
        self.setWindowIcon(QIcon('window_logo.ico'))

        # Tool bar（分为两个action：新建截图或者确认并退出）
        exitAction = QAction(QIcon('save_close.png'),'checked',self)
        exitAction.setShortcut('Alt+W')
        exitAction.triggered.connect(qApp.quit)
        self.toolbar = self.addToolBar('toolbar')
        self.toolbar.addAction(exitAction)

        newAction = QAction(QIcon('screenshot.png'),'re-snipping',self)
        newAction.setShortcut('Alt+Q')
        newAction.triggered.connect(self.switch)
        self.toolbar.addAction(newAction)

        # Add text field
        self.textView = QTextEdit(self)
        # self.b.setStyleSheet("""QPlainTextEdit {color: #00FF00;
        #                    font-family: Courier;}""")
        # main_window.setCentralWidget(self.b)
        # self.b.textChanged.connect(lambda: print(self.b.document().toPlainText()))
        self.textView.insertPlainText('*Snipping contents are recognized as below.*\n'
                                      '*Click checked(Alt+W) to paste text from clipboard or click Re-snipping(Alt+Q).*\n'
                                      '------------------------------------------------------------------------------------\n')

        self.textView.move(5, 40)
        self.textView.setMinimumSize(510, 275)
        QApplication.clipboard().dataChanged.connect(self.clipboardChanged)

        # 居中显示处理
        self.move_center()

    def move_center(self):
        screen = QDesktopWidget().screenGeometry()
        form = self.geometry()
        x_move_step = (screen.width() - form.width()) / 2
        y_move_step = (screen.height() - form.height()) / 2
        self.move(x_move_step, y_move_step)

    def clipboardChanged(self):
        text = QApplication.clipboard().text()  # Get the system clipboard contents
        self.textView.insertPlainText(text + '\n')

    def switch(self):
        self.switch_window.emit()
        self.close()


class Controller:
    """ 控制类（用close()和show()来控制页面的跳转的顺序）
    """
    def __init__(self):
        pass

    def show_language(self):
        self.firstwindow = LanguageSelect()
        self.firstwindow.switch_window.connect(self.show_snipping)
        self.firstwindow.show()

    def show_snipping(self, text):
        self.secwindow = Snipping(text)
        self.secwindow.switch_window.connect(self.show_clipboard)
        self.firstwindow.close()
        self.secwindow.show()

    def show_clipboard(self):
        self.thirdwindow = ContentShow()
        self.thirdwindow.switch_window.connect(self.show_language)
        self.secwindow.close()
        self.thirdwindow.show()


def processImage(img):
    """ 使用pytesseract识别英文内容的函数
    """
    buffer = QtCore.QBuffer()
    buffer.open(QtCore.QBuffer.ReadWrite)
    img.save(buffer, "PNG")
    pil_img = Image.open(io.BytesIO(buffer.data()))
    buffer.close()

    try:
        result = pytesseract.image_to_string(
            pil_img, timeout=2, lang=(sys.argv[1] if len(sys.argv) > 1 else None)
        )
    except RuntimeError as error:
        print(f"ERROR: An error occurred when trying to process the image: {error}")
        return

    if result:
        pyperclip.copy(result)
        print(f'INFO: Copied "{result}" to the clipboard')
    else:
        print(f"INFO: Unable to read text from image, did not copy")


def getOCR(img):
    """使用CnOcr识别图片内容，按行输出结果至res列表的函数
    """
    global result_str, result
    buffer = QtCore.QBuffer()
    buffer.open(QtCore.QBuffer.ReadWrite)
    img.save(buffer, "PNG")
    pil_img = Image.open(io.BytesIO(buffer.data()))
    image_array = np.array(pil_img)
    buffer.close()

    ocr = CnOcr()
    res = ocr.ocr(image_array)

    try:
        # 拼接字符串并保存至results列表
        result_str = []
        for iter_item in res:
            result_str.append(''.join(iter_item))
        result = "\n".join(result_str)

    except (ZeroDivisionError,Exception) :
        print(ZeroDivisionError, ":", Exception)
        print(f"INFO: Unable to read text from image, did not copy")

    if result:
        pyperclip.copy(result)
        print(f'INFO: Copied "{result}" to the clipboard')
    else:
        print(f"INFO: Unable to read text from image, did not copy")


def notify(msg):
    try:
        Notification(title="TextShot", description=msg).send()
    except (SystemError, NameError):
        trayicon = QtWidgets.QSystemTrayIcon(
            QtGui.QIcon(
                QtGui.QPixmap.fromImage(QtGui.QImage(1, 1, QtGui.QImage.Format_Mono))
            )
        )
        trayicon.show()
        trayicon.showMessage("TextShot", msg, QtWidgets.QSystemTrayIcon.NoIcon)
        trayicon.hide()


def main():
    app = QApplication(sys.argv)
    controller = Controller()
    controller.show_language()
    sys.exit(app.exec_())


if __name__ == "__main__":      #只有从当前应用程序直接运行TextshotApp.py才会调用
    try:
        pytesseract.get_tesseract_version()
    except EnvironmentError:
        notify(
            "Tesseract is either not installed or cannot be reached.\n"
            "Have you installed it and added the install directory to your system path?"
        )
        print(
            "ERROR: Tesseract is either not installed or cannot be reached.\n"
            "Have you installed it and added the install directory to your system path?"
        )
        sys.exit()
    main()
