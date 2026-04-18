module.exports = {
  apps: [
    {
      name: "caren-backend",
      script: "main_api.py",
      interpreter: ".venv/bin/python", // Path to your virtual env python
      env: {
        NODE_ENV: "production",
      },
      // Restarts the backend if it crashes
      exp_backoff_restart_delay: 100,
    },
    {
      name: "caren-frontend",
      script: "npm",
      args: "run dev",
      cwd: "./caren-ui",
      env: {
        NODE_ENV: "production",
      }
    }
  ]
};