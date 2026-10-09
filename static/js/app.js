function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    return decodeURIComponent(parts.pop().split(';').shift());
  }
  return '';
}

function showWorkflowStatus(message, isError = false) {
  const statusNode = document.getElementById('project-flow-status');
  if (!statusNode) return;

  statusNode.textContent = message;
  statusNode.classList.toggle('error', isError);
}

document.addEventListener('DOMContentLoaded', () => {
  const yearTarget = document.getElementById('year');
  if (yearTarget) {
    yearTarget.textContent = new Date().getFullYear();
  }

  const workflowForm = document.getElementById('project-workflow-form');
  if (!workflowForm) return;

  workflowForm.addEventListener('submit', async (event) => {
    const fileInput = workflowForm.querySelector('input[type="file"]');
    if (!fileInput || !fileInput.files.length) {
      return;
    }

    event.preventDefault();
    showWorkflowStatus('Creating project and uploading document...');

    const csrfToken = getCookie('csrftoken');
    const metadata = new FormData(workflowForm);
    metadata.delete('file');

    try {
      const projectResponse = await fetch(workflowForm.action || window.location.href, {
        method: 'POST',
        body: metadata,
        headers: {
          'X-CSRFToken': csrfToken,
          'X-Requested-With': 'XMLHttpRequest',
        },
        credentials: 'same-origin',
      });

      if (!projectResponse.ok) {
        const errorText = await projectResponse.text();
        throw new Error(errorText || 'Unable to create the project.');
      }

      const projectData = await projectResponse.json();
      const uploadData = new FormData();
      uploadData.append('file', fileInput.files[0]);
      uploadData.append('project_id', projectData.project_id);

      const uploadResponse = await fetch('/api/documents/upload/', {
        method: 'POST',
        body: uploadData,
        headers: {
          'X-CSRFToken': csrfToken,
          'X-Requested-With': 'XMLHttpRequest',
        },
        credentials: 'same-origin',
      });

      if (!uploadResponse.ok) {
        const errorData = await uploadResponse.json().catch(() => ({}));
        throw new Error(errorData.error || 'The document upload failed.');
      }

      showWorkflowStatus(`Project created. Your file is being processed for ${projectData.project_name}.`);
      window.setTimeout(() => {
        window.location.href = '/dashboard/';
      }, 1200);
    } catch (error) {
      showWorkflowStatus(error.message || 'Something went wrong while creating the project.', true);
    }
  });
});
