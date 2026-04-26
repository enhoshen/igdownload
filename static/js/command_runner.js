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
        if (formData.has(key)) {
          currentCommandParts.push(`--${key}`);
        }
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

  updateCommandDisplay();
});
