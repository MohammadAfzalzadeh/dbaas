const { createLogger, format, transports } = require('winston');
const DailyRotateFile = require('winston-daily-rotate-file');
const path = require('path');

const LOG_PATH = process.env.LOG_PATH || '/var/log';
const LOG_LEVEL = process.env.LOG_LEVEL || 'info';
const LOG_MAX_SIZE = process.env.LOG_MAX_SIZE || '20m';
const LOG_MAX_FILES = process.env.LOG_MAX_FILES || '30d';


const logger = createLogger({
  level: 'info',
  format: format.combine(
    format.timestamp(),
    format.json()
  ),
  transports: [
    new transports.Console(),

    new DailyRotateFile({
      filename: path.join(LOG_PATH, 'pgcat-config-watcher-%DATE%.log'), 
      datePattern: 'YYYY-MM-DD',
      zippedArchive: true, 
      maxSize: LOG_MAX_SIZE, 
      maxFiles: LOG_MAX_FILES, 
      level: LOG_LEVEL
    }),
  ]
});


function log(level, message, extra = {}) {
    logger.log({
      level,
      message,
      ...extra
    });
  }

module.exports = {log};
