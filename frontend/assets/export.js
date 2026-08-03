window.dash_clientside = window.dash_clientside || {};
window.dash_clientside.clientside = window.dash_clientside.clientside || {};

window.dash_clientside.clientside.export_pdf = function(n_clicks) {
    if (!n_clicks) return window.dash_clientside.no_update;
    const element = document.getElementById('main-content') || document.body;
    const { jsPDF } = window.jspdf;
    
    // Temporarily hide buttons for export
    const downloadButtons = document.querySelectorAll('.download-chart-btn, .dashboard-export-dropdown');
    downloadButtons.forEach(btn => btn.style.display = 'none');
    
    html2canvas(element, { scale: 2, useCORS: true }).then(canvas => {
        downloadButtons.forEach(btn => btn.style.display = '');
        const imgData = canvas.toDataURL('image/jpeg', 0.95);
        const pdf = new jsPDF('p', 'mm', 'a4');
        const imgWidth = 210; // A4 width
        const pageHeight = 297; // A4 height
        const imgHeight = (canvas.height * imgWidth) / canvas.width;
        let heightLeft = imgHeight;
        let position = 0;

        pdf.addImage(imgData, 'JPEG', 0, position, imgWidth, imgHeight);
        heightLeft -= pageHeight;

        while (heightLeft >= 0) {
            position = heightLeft - imgHeight;
            pdf.addPage();
            pdf.addImage(imgData, 'JPEG', 0, position, imgWidth, imgHeight);
            heightLeft -= pageHeight;
        }
        pdf.save('dashboard.pdf');
    }).catch(err => {
        downloadButtons.forEach(btn => btn.style.display = '');
        console.error('PDF export failed:', err);
    });
    return '';
};

window.dash_clientside.clientside.export_jpg = function(n_clicks) {
    if (!n_clicks) return window.dash_clientside.no_update;
    const element = document.getElementById('main-content') || document.body;
    
    const downloadButtons = document.querySelectorAll('.download-chart-btn, .dashboard-export-dropdown');
    downloadButtons.forEach(btn => btn.style.display = 'none');
    
    html2canvas(element, { scale: 2, useCORS: true }).then(canvas => {
        downloadButtons.forEach(btn => btn.style.display = '');
        const link = document.createElement('a');
        link.download = 'dashboard.jpg';
        link.href = canvas.toDataURL('image/jpeg', 0.95);
        link.click();
    }).catch(err => {
        downloadButtons.forEach(btn => btn.style.display = '');
        console.error('JPG export failed:', err);
    });
    return '';
};

window.dash_clientside.clientside.export_chart_jpg = function(n_clicks, graphId) {
    if (!n_clicks) return window.dash_clientside.no_update;
    
    // Find the plotly gd element
    const gd = document.getElementById(graphId);
    if (gd) {
        const plotEl = gd.querySelector('.js-plotly-plot') || gd;
        if (window.Plotly) {
            window.Plotly.downloadImage(plotEl, {
                format: 'jpeg',
                filename: graphId + '_chart',
                height: plotEl.clientHeight || 500,
                width: plotEl.clientWidth || 700
            });
        } else {
            // Fallback html2canvas
            html2canvas(gd, { scale: 2, useCORS: true }).then(canvas => {
                const link = document.createElement('a');
                link.download = graphId + '.jpg';
                link.href = canvas.toDataURL('image/jpeg', 0.95);
                link.click();
            });
        }
    }
    return '';
};
