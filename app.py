from ip_app import app, scheduler
import ip_app.models as models


if __name__ == '__main__':
    scheduler.start()
    app.run(debug=True, host='0.0.0.0', port=5000)
