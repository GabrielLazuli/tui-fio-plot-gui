import shutil

import plot_app


try:
    plot_app.main_gui()
finally:
    shutil.rmtree(plot_app.TMP_ROOT, ignore_errors=True)
