const STORAGE_ITEM_DATA_KEY = "my-survey-data";
const STORAGE_ITEM_UI_STATE_KEY = "my-survey-state";

document.addEventListener("DOMContentLoaded", function () {
  console.log('starting survey...')

  function downloadFile(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.style.display = "none";
    document.body.appendChild(link);
    link.click();
    URL.revokeObjectURL(url);
    document.body.removeChild(link);
  }

  function restoreSurveyProgress(survey) {
    const savedData = localStorage.getItem(STORAGE_ITEM_DATA_KEY);
    const savedUIState = localStorage.getItem(STORAGE_ITEM_UI_STATE_KEY);

    if (savedData) {
        survey.data = JSON.parse(savedData);
    }
    if (savedUIState) {
        const uiState = JSON.parse(savedUIState);
        survey.currentPageNo = uiState.currentPageNo;
    }
  }

  function appendInfoLink(text, element) {
    // encodeURIComponent doesn't encode - & , which have special meaning in text fragments
    const textFragment = encodeURIComponent(text.trim())
      .replace(/-/g, '%2D')
      .replace(/&/g, '%26')
      .replace(/,/g, '%2C');
    const infoLink = document.createElement('a');
    infoLink.href = `/informative-survey#:~:text=${textFragment}`;
    infoLink.target = '_blank';
    infoLink.rel = 'noopener noreferrer';
    infoLink.className = 'inline-flex ml-2';
    infoLink.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>';
    infoLink.title = 'More information';
    element.appendChild(infoLink);
  }

  function downloadSurveyData(survey) {
    const surveyDataJson = JSON.stringify(survey.data, null, 2);
    const jsonBlob = new Blob([surveyDataJson], { type: "application/json" });
    downloadFile(jsonBlob, "survey-data.json");
  }

  async function surveyComplete(survey) {
    try {
      const response = await fetch("/submit", {
        method: "POST",
        headers: {
          "Content-Type": "application/json;charset=UTF-8",
        },
        body: JSON.stringify(survey.data),
      });

      if (response.ok) {
        const blob = await response.blob();
        downloadFile(blob, "survey-result");
      } else {
        const errorText = await response.text();
        console.error("Submission failed:", response.status, errorText);
        alert(`Failed to submit survey: ${response.status} ${response.statusText}\n${errorText}`);
      }
    } catch (error) {
      console.error("Submission error:", error);
      alert(`An error occurred while submitting the survey: ${error.message}`);
    }
  }

  const survey = new Survey.Model(window.config);
  survey.onComplete.add(surveyComplete);
  survey.applyTheme(THEME);

  survey.onValueChanged.add((sender, options) => {
    const data = sender.data;
    localStorage.setItem(STORAGE_ITEM_DATA_KEY, JSON.stringify(data));
  });

  survey.onCurrentPageChanged.add((sender, options) => {
    const uiState = { currentPageNo: sender.currentPageNo };
    localStorage.setItem(STORAGE_ITEM_UI_STATE_KEY, JSON.stringify(uiState));
  });

  survey.addNavigationItem({
    id: "sv-nav-clear-page",
    title: "Clear Page",
    action: () => {
      survey.currentPage.questions.forEach((question) => {
          question.value = undefined;
      });
    },
    css: "nav-button",
    innerCss: "sd-btn"
  });

  survey.addNavigationItem({
    id: "sv-nav-download-page",
    title: "Download survey configuration",
    action: () => {
      downloadSurveyData(survey);
    },
    css: "nav-button",
    innerCss: "sd-btn"
  });

  survey.addNavigationItem({
    id: "sv-nav-upload-state",
    title: "Upload survey state",
    action: () => {
      const fileInput = document.createElement("input");
      fileInput.type = "file";
      fileInput.accept = ".json,application/json";
      fileInput.style.display = "none";
      fileInput.addEventListener("change", (event) => {
        const file = event.target.files[0];
        if (file) {
          const reader = new FileReader();
          reader.onload = (e) => {
            try {
              const data = JSON.parse(e.target.result);
              survey.data = data;
              localStorage.setItem(STORAGE_ITEM_DATA_KEY, JSON.stringify(data));
            } catch (error) {
              console.error("Failed to parse JSON file:", error);
              alert("Invalid JSON file. Please upload a valid survey state file.");
            }
          };
          reader.readAsText(file);
        }
        document.body.removeChild(fileInput);
      });
      document.body.appendChild(fileInput);
      fileInput.click();
    },
    css: "nav-button",
    innerCss: "sd-btn"
  });

  DOMPurify.addHook("afterSanitizeAttributes", function (node) {
    // set all elements owning target to target=_blank
    if ("target" in node) {
      node.setAttribute("target", "_blank");
      node.setAttribute("rel", "noopener noreferrer");
    }
    // set non-HTML/MathML links to xlink:show=new
    if (
      !node.hasAttribute("target") &&
      (node.hasAttribute("xlink:href") || node.hasAttribute("href"))
    ) {
      node.setAttribute("xlink:show", "new");
    }
  });

  survey.addNavigationItem({
    id: "sv-nav-clear-all",
    title: "Clear All",
    action: () => {
      if (confirm("Are you sure you want to clear all survey data? This action cannot be undone.")) {
        survey.clear();
        localStorage.removeItem(STORAGE_ITEM_DATA_KEY);
        localStorage.removeItem(STORAGE_ITEM_UI_STATE_KEY);
      }
    },
    css: "nav-button",
    innerCss: "sd-btn"
  });

  survey.onTextMarkdown.add((_, options) => {
    const sanitized = DOMPurify.sanitize(marked.parse(options.text));
    if (sanitized.startsWith("<p>")) {
      options.html = sanitized.substring(3, sanitized.length - 5);
    } else {
      options.html = sanitized;
    }
  });

  survey.onAfterRenderQuestion.add((sender, options) => {
    const questionElement = options.htmlElement;
    let titleElement = questionElement.querySelector('.sd-question__title');

      if (titleElement && options.question.title && !options.question.title.match(/^\*(warning|note):\s/i)) {
        titleElement = titleElement.querySelector('.sv-title-actions__title') || titleElement;
        appendInfoLink(options.question.title, titleElement);
      }
  });

  restoreSurveyProgress(survey);

  survey.render(document.getElementById("survey"));
});
