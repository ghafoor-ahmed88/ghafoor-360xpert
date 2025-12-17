const { Sequelize } = require('sequelize');

const sequelize = new Sequelize(
  'fastifydb',      // Database name
  'admin',          // DB user
  'admin123',       // DB password
  {
    host: 'localhost',
    port: 5433,     // Docker mapped port
    dialect: 'postgres',
    logging: false
  }
);

module.exports = sequelize;