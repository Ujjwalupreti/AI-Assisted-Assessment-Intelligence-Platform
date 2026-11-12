import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './app';
// <CheckCircle size={18} className="me-2" /> FIXED IMPORT: Notice the curly braces { } below
import { AuthProvider } from './AuthContext'; 
import { BrowserRouter } from 'react-router-dom';
import 'bootstrap/dist/css/bootstrap.min.css';
import './app.css';
import { CheckCircle } from 'lucide-react';


ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
);