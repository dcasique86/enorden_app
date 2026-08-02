const fs = require('fs');
const path = 'tecnosport_app/static/js/app.js';
try {
    const content = fs.readFileSync(path, 'utf8');
    const cleaned = content.replace(/\0/g, '');
    fs.writeFileSync(path, cleaned, 'utf8');
    console.log('File cleaned successfully. Original length:', content.length, 'Cleaned length:', cleaned.length);
} catch (err) {
    console.error('Error cleaning file:', err);
}
