document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('form');
  const commandDisplayCode = document.getElementById('dynamic-command-display').querySelector('code');

  // Data expected to be provided via window.APP_CONFIG in the HTML template
  const scriptArguments = window.APP_CONFIG.scriptArguments;
  const baseCommand = window.APP_CONFIG.baseCommand;

  const updateCommandDisplay = () => {
    const formData = new FormData(form);
    const currentCommandParts = [...baseCommand];

    formData.forEach((value, key) => {
      const argDef = scriptArguments.find(arg => arg.dest === key);
      if (!argDef) return;

      if (argDef.type === 'checkbox') {
        // if (formData.has(key)) { // This check is commented out, assuming checkboxes are always present if checked
        currentCommandParts.push(`--${key}`);
        // }
      } else if (value !== '') {
        currentCommandParts.push(`--${key}`);
        currentCommandParts.push(value);
      }
    });
    commandDisplayCode.textContent = currentCommandParts.join(' ');
  };

  // add listener for each input fields
  const formElements = form.querySelectorAll('input, select');
  formElements.forEach(element => {
    element.addEventListener('input', updateCommandDisplay);
    element.addEventListener('change', updateCommandDisplay);
  });

  // Add paste functionality
  const pasteButtons = document.querySelectorAll('.btn-paste');
  pasteButtons.forEach(button => {
    button.addEventListener('click', async () => {
      try {
        const text = await navigator.clipboard.readText();
        
        // The paste button is now directly inside the input-row div.
        const inputRow = button.parentElement; 
        
        let targetInput = null;
        if (inputRow) {
          // Find the first input or select element within inputRow
          // We are looking for input[type="search"] or select elements.
          targetInput = inputRow.querySelector('input[type="search"], select');
        }

        if (targetInput) {
          targetInput.value = text;
          // For select elements, find the option if it exists and select it.
          if (targetInput.tagName === 'SELECT') {
            const option = targetInput.querySelector(`option[value="${text}"]`);
            if (option) {
              option.selected = true;
            }
            // If no option matches, the value is set, but no option is selected.
            // This is acceptable for a basic paste functionality.
          }
          
          // Dispatch input/change event to potentially trigger other listeners (like updateCommandDisplay)
          const eventType = targetInput.tagName === 'SELECT' ? 'change' : 'input';
          const event = new Event(eventType, { bubbles: true });
          targetInput.dispatchEvent(event);

        } else {
          console.warn('Target input element not found for paste button.');
        }
      } catch (err) {
        console.error('Failed to read clipboard content: ', err);
        alert('Failed to paste. Please grant clipboard access or try again.');
      }
    });
  });

  updateCommandDisplay();
});
