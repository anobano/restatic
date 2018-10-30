
import pytest
import io
import peewee
from PyQt5.QtWidgets import QApplication
from PyQt5 import QtCore

import vorta.borg_runner
import vorta.models
from vorta.views.main_window import MainWindow
from vorta.views.repo_add import AddRepoWindow
from vorta.tray_menu import TrayMenu
from vorta.scheduler import init_scheduler
from vorta.models import BackupProfileModel, EventLogModel, RepoModel


@pytest.fixture()
def main(tmpdir, qtbot):
    tmp_db = tmpdir.join('settings.sqlite')
    mock_db = peewee.SqliteDatabase(str(tmp_db))
    vorta.models.init_db(mock_db)

    app = QApplication([])
    app.thread = None
    app.setQuitOnLastWindowClosed(False)
    app.scheduler = init_scheduler()
    TrayMenu(app)
    app.profile = BackupProfileModel.get(id=1)

    main = MainWindow(app)
    main.show()
    qtbot.addWidget(main)

    return main


def test_repo_tab(main, qtbot, mocker):
    qtbot.mouseClick(main.createStartBtn, QtCore.Qt.LeftButton)
    assert main.createProgressText.text() == 'Add a remote backup repository first.'

    qtbot.mouseClick(main.createStartBtn, QtCore.Qt.LeftButton)


def test_repo_add(main, qtbot, mocker):
    # Add new repo window
    add_repo_window = AddRepoWindow(main)
    qtbot.addWidget(add_repo_window)
    add_repo_window.show()
    qtbot.keyClicks(add_repo_window.repoURL, 'aaa')
    qtbot.mouseClick(add_repo_window.saveButton, QtCore.Qt.LeftButton)
    assert add_repo_window.errorText.text() == 'Please enter a valid repo URL including hostname and path.'

    qtbot.keyClicks(add_repo_window.repoURL, 'bbb.com:repo')
    qtbot.mouseClick(add_repo_window.saveButton, QtCore.Qt.LeftButton)
    assert add_repo_window.errorText.text() == 'Please use a longer password.'

    qtbot.keyClicks(add_repo_window.passwordLineEdit, 'long-password-long')

    popen_result =mocker.MagicMock(stdout=io.StringIO("some initial binary data"),
                              stderr=io.StringIO("some initial binary data"),
                              returncode=0)
    mocker.patch.object(vorta.borg_runner, 'Popen', return_value=popen_result)

    qtbot.mouseClick(add_repo_window.saveButton, QtCore.Qt.LeftButton)

    with qtbot.waitSignal(add_repo_window.thread.result, timeout=1000) as blocker:
        pass

    main.repoTab.process_new_repo(blocker.args[0])

    assert EventLogModel.select().count() == 1
    assert RepoModel.get(id=1).url == 'aaabbb.com:repo'
