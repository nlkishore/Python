import os

structure = {
    "my-web-app": {
        "public": {},
        "src": {
            "routes": {
                "index.js": """
const express = require('express');
const router = express.Router();

router.get('/', (req, res) => {
  res.json({ message: 'Hello, world!' });
});

module.exports = router;
"""
            },
            "app.js": """
const express = require('express');
const dotenv = require('dotenv');
const routes = require('./routes/index');

dotenv.config();
const app = express();

app.use(express.json());
app.use(express.static('public'));
app.use('/api', routes);

app.listen(process.env.PORT || 3000, () =>
  console.log(`Server running on port ${process.env.PORT || 3000}`)
);
"""
        },
        ".env": "PORT=3000",
        ".gitignore": "node_modules\n.env",
        "package.json": """
{
  "name": "my-web-app",
  "version": "1.0.0",
  "main": "src/app.js",
  "scripts": {
    "dev": "nodemon src/app.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "dotenv": "^10.0.0"
  },
  "devDependencies": {
    "nodemon": "^2.0.7"
  }
}
""",
        "README.md": "# My Express Web App"
    }
}

def create_structure(base, tree):
    for name, content in tree.items():
        path = os.path.join(base, name)
        if isinstance(content, dict):
            os.makedirs(path, exist_ok=True)
            create_structure(path, content)
        else:
            with open(path, "w") as f:
                f.write(content.strip())

create_structure(".", structure)
print("Express scaffold generated!")