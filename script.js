// ConsentGraph Website - JavaScript

// Smooth scrolling is handled by CSS scroll-behavior: smooth

// Add animation on scroll
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -100px 0px'
};

const observer = new IntersectionObserver(function(entries) {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, observerOptions);

// Observe cards and sections
document.addEventListener('DOMContentLoaded', () => {
    const cards = document.querySelectorAll('.card, .feature-card, .metric-card, .pattern-card, .finding-group');
    
    cards.forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(card);
    });
});

// Mobile menu toggle
const navLinks = document.querySelector('.nav-links');
if (navLinks) {
    navLinks.addEventListener('click', (e) => {
        if (e.target.tagName === 'A') {
            // Smooth scroll is handled by CSS
        }
    });
}

// Track clicks for analytics (if you want to add Google Analytics)
document.addEventListener('click', (e) => {
    if (e.target.tagName === 'A' && e.target.href.includes('github')) {
        console.log('GitHub link clicked:', e.target.href);
        // Add GA tracking if needed
    }
});

// Page visibility
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        console.log('Page hidden');
    } else {
        console.log('Page visible');
    }
});

// Counter animation for stats
function animateCounters() {
    const counters = document.querySelectorAll('.stat-number, .metric-value, .sector-score, .ns-number');
    
    counters.forEach(counter => {
        const target = parseInt(counter.textContent);
        const increment = target / 30;
        let current = 0;
        
        const updateCounter = () => {
            current += increment;
            if (current < target) {
                counter.textContent = Math.floor(current);
                requestAnimationFrame(updateCounter);
            } else {
                counter.textContent = target;
            }
        };
        
        // Only animate when visible
        const counterObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    updateCounter();
                    counterObserver.unobserve(entry.target);
                }
            });
        });
        
        counterObserver.observe(counter);
    });
}

// Initialize counter animations
document.addEventListener('DOMContentLoaded', animateCounters);

// Print friendly version
function printPage() {
    window.print();
}

// Share functionality
function shareToTwitter() {
    const text = 'ConsentGraph - Privacy compliance analysis reveals 87.5% of websites violate DPDP Act 2023';
    const url = window.location.href;
    const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`;
    window.open(twitterUrl, '_blank');
}

function shareToLinkedIn() {
    const url = window.location.href;
    const linkedInUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`;
    window.open(linkedInUrl, '_blank');
}

// Copy email to clipboard
function copyEmail() {
    const email = 'contact@consentgraph.dev';
    navigator.clipboard.writeText(email).then(() => {
        alert('Email copied to clipboard!');
    });
}

// Dark mode toggle (optional)
function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
    localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
}

// Check dark mode preference
function checkDarkModePreference() {
    const darkMode = localStorage.getItem('darkMode');
    if (darkMode === 'true') {
        document.body.classList.add('dark-mode');
    }
}

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    checkDarkModePreference();
    
    // Add version info
    console.log('%cConsentGraph v1.0.0', 'color: #667eea; font-size: 16px; font-weight: bold;');
    console.log('%cPrivacy compliance analysis for DPDP Act 2023', 'color: #666; font-size: 12px;');
    console.log('%cGitHub: https://github.com/consentgraph', 'color: #999; font-size: 12px;');
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Press '?' for help
    if (e.key === '?') {
        console.log('ConsentGraph Keyboard Shortcuts:');
        console.log('? - Show this help');
        console.log('G - Go to GitHub');
    }
    
    // Press 'G' to go to GitHub
    if (e.key === 'g' || e.key === 'G') {
        window.location.href = 'https://github.com/consentgraph';
    }
});

// Performance monitoring
if (window.performance) {
    window.addEventListener('load', () => {
        const perfData = window.performance.timing;
        const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart;
        console.log('Page load time:', pageLoadTime, 'ms');
    });
}

// Accessibility: Ensure focus is visible
document.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
        document.body.classList.add('keyboard-nav');
    }
});

document.addEventListener('mousedown', () => {
    document.body.classList.remove('keyboard-nav');
});

// Service Worker registration for PWA (optional)
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {
        // Service worker not available
    });
}
