# 1. Start or Restart the Backend
pm2 describe $APP_NAME_BACKEND > /dev/null
if [ $? -eq 0 ]; then
    echo "♻️ Restarting existing Backend instance..."
    pm2 restart $APP_NAME_BACKEND
else
    echo "📡 Starting fresh Backend instance..."
    pm2 start $PYTHON_VENV --name $APP_NAME_BACKEND -- $BACKEND_SCRIPT
fi

# 2. Start or Restart the Frontend
pm2 describe $APP_NAME_FRONTEND > /dev/null
if [ $? -eq 0 ]; then
    echo "♻️ Restarting existing Frontend instance..."
    pm2 restart $APP_NAME_FRONTEND
else
    echo "💻 Starting fresh Frontend instance..."
    cd $FRONTEND_PATH
    pm2 start npm --name $APP_NAME_FRONTEND -- run dev
fi