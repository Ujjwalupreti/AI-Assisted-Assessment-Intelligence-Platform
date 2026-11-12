import CryptoJS from 'crypto-js';

// Encrypts a plain text string into AES-256 Ciphertext
export const encryptText = (text, password) => {
    if (!text || !password) return text;
    return CryptoJS.AES.encrypt(text, password).toString();
};

// Decrypts Ciphertext back to readable text
export const decryptText = (cipherText, password) => {
    if (!cipherText || !password) return cipherText;
    try {
        const bytes = CryptoJS.AES.decrypt(cipherText, password);
        const originalText = bytes.toString(CryptoJS.enc.Utf8);
        if (!originalText) throw new Error("Invalid decryption key");
        return originalText;
    } catch (error) {
        return " [Encrypted Data - Wrong Password]";
    }
};

// Hashes text (one-way) so the server can grade without knowing the answer
export const hashText = (text) => {
    if (!text) return text;
    // We use SHA-256 to create a secure, irreversible hash
    return CryptoJS.SHA256(text).toString();
};