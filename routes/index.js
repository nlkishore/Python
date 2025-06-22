// routes/index.js
const express = require('express');
const router = express.Router();

// Home page route
router.get('/', (req, res) => {
  res.render('index', { title: 'Express Modular App', message: 'Welcome to your modular Express app!' });
});

module.exports = router;
