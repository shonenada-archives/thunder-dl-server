# -*- coding: utf-8 -*-

import os
import sys
import time
from ctypes import windll, c_ulong, c_wchar_p, c_long, c_ulonglong, byref

import errors


SAVE_PATH = ''


class Thunder(object):

    def __init__(self):
        self.thunder = windll.LoadLibrary('XLDownload')

    def init(self):
        result = self.thunder.XLInitDownloadEngine()
        if result == 0:
            raise RuntimeError('Thunder init failed')

    def shutdown(self):
        result = self.thunder.XLUninitDownloadEngine()
        if result == 0:
            raise RuntimeError('Thunder uninit failed')

    def get_task_info(self, task_id):
        status = c_long()
        file_size = c_ulonglong()
        recv_size = c_ulonglong()
        err_id = self.thunder.XLQueryTaskInfo(
            task_id,
            byref(status),
            byref(file_size),
            byref(recv_size),
        )

        return (err_id, int(status.value),
                int(file_size.value), int(recv_size.value))

    def continue_task(self, task_id):
        err_id = self.thunder.XLContinueTask(task_id)
        return err_id

    def stop_task(self, task_id):
        err_id = self.thunder.XLStopTask(task_id)
        return err_id

    def pause_task(self, task_id):
        new_task_id = c_long()
        err_id = self.thunder.XLPauseTask(task_id, byref(new_task_id))
        return err_id, int(new_task_id.value)

    def _download_impl(self, save_path, url, ref_url=None):
        """Download file to path

        :param save_path: path which downloaded files will be saved in.
        :param url: URL wait to download.
        :param ref_url: Reference URL, can be `None`
        """
        task_id = c_ulong(0)
        c_save_path = c_wchar_p(save_path)
        c_url = c_wchar_p(url)
        c_ref_url = c_wchar_p(ref_url)
        c_task_id = byref(task_id)
        err_id = self.thunder.XLURLDownloadToFile(
            c_save_path,
            c_url,
            c_ref_url,
            c_task_id, )
        return err_id, int(task_id.value)

    def _polling_for_download(self, task_id, url, **kwargs):
        progress_callback = kwargs.get('progress_callback', None)
        success_callback = kwargs.get('success_callback', None)
        error_callback = kwargs.get('error_callback', None)

        while True:
            time.sleep(1)
            err_id, status, file_size, recv_size = self.get_task_info(task_id)

            if err_id != errors.SUCCESS:
                if error_callback is not None:
                    error_callback(url)
                self.stop_task(task_id)
                return False, err_id

            if status == errors.TASK_CONNECT or status == errors.TASK_PAUSE:
                # Do nothing
                pass

            elif status == errors.TASK_DOWNLOAD:
                if progress_callback is not None:
                    progress_callback(url, recv_size, file_size)

            elif status == errors.TASK_SUCCESS:
                self.stop_task(task_id)
                if success_callback is not None:
                    success_callback(url, file_size)
                return True, None

            elif status == errors.TASK_FAIL:
                if error_callback is not None:
                    error_callback(url)
                break
        self.stop_task(task_id)
        return False, None

    def sync_download(self, save_path, url, ref_url=None, **kwargs):
        """Download files.

        :param save_path: path which downloaded files will be saved in.
        :param url: URL wait to download.
        :param ref_url: Reference URL, can be `None`
        :param progress_callback: Callback function for progressing.
        :param success_callback: Callback function of downloading successfully.
        :param error_callback: Callback function when fail to download.
        """

        err_id, task_id = self._download_impl(save_path, url, ref_url)
        progress_callback = kwargs.get('progress_callback', None)
        success_callback = kwargs.get('success_callback', None)
        error_callback = kwargs.get('error_callback', None)

        if err_id != errors.SUCCESS:
            if error_callback:
                error_callback(url)
            return False, err_id

        return self._polling_for_download(
            task_id, url,
            progress_callback=progress_callback,
            success_callback=success_callback,
            error_callback=error_callback,
        )


def progressbar(percent, prefix='', size=30):
    width = int(size * percent)
    sys.stdout.write("\r%s[%s%s] %.2f%%" % (prefix,
                                            "#" * width,
                                            "." * (size-width),
                                            percent * 100.0))
    sys.stdout.flush()


def main():
    if len(sys.argv) < 2:
        url = raw_input('URL:')
    else:
        url = sys.argv[1]

    def progress_cb(url, recv_size, file_size):
        if file_size > 0:
            percent = float(recv_size) / float(file_size)
            progressbar(percent, 'Downloading: ')

    thunder = Thunder()
    thunder.init()

    name = url.rsplit('/', 1)[-1]
    file_path = os.path.join(SAVE_PATH, name)
    thunder.sync_download(
        file_path, url,
        progress_callback=progress_cb
    )

    thunder.shutdown()


if __name__ == '__main__':
    main()
