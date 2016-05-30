# -*- coding: utf-8 -*-

import os

from flask import Flask, request, redirect, url_for, abort, jsonify

from libs.thunder import Thunder


app = Flask(__name__)

save_path = os.environ.get('THUNDER_SAVE_PATH')
thunder = Thunder()
thunder.init()
tasks_db = {}


def prg_cb(task_id, url, recv_size, file_size):
    tasks_db[task_id] = (url, recv_size, file_size)


def success_cb(task_id, url, file_size):
    del tasks_db[task_id]


def error_cb(task_id, url, file_size):
    tasks_db[task_id] = (False, False, False)


@app.route('/')
def index():
    html = ('<form action="/tasks" method="POST">'
            '  <input type="text" name="url" />'
            '  <input type="submit" value="submit" />'
            '</form>')

    return html


@app.route('/tasks', methods=['POST'])
def tasks():
    url = request.form.get('url', None)

    if url is None:
        return redirect(url_for('index'))

    thunder.sync_download(
        file_path=save_path,
        url=url,
        progress_callback=prg_cb,
        success_callback=success_cb,
        error_callback=error_cb,
    )
    return jsonify({'success': True})


@app.route('/tasks/<int:tid>', methods=['GET'])
def task(task_id):
    t = tasks_db.get(task_id, None)

    if t is None:
        return abort(404)

    if t[0] is False and t[1] is False and t[2] is False:
        return abort(404)

    return jsonify(t)
