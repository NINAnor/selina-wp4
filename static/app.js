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

  async function surveyComplete(survey) {
    try {
      // First, download the survey data as JSON
      const surveyDataJson = JSON.stringify(survey.data, null, 2);
      const jsonBlob = new Blob([surveyDataJson], { type: "application/json" });
      downloadFile(jsonBlob, "survey-data.json");

      // Then, send the POST request
      const response = await fetch("/submit", {
        method: "POST",
        headers: {
          "Content-Type": "application/json;charset=UTF-8",
        },
        body: JSON.stringify(survey.data),
      });

      console.log(response);

      if (response.ok) {
        const blob = await response.blob();
        downloadFile(blob, "survey-result");
      } else {
        // TODO: Handle error
      }
    } catch (error) {
      // TODO: Handle error
      console.error(error);
    }
  }

  const survey = new Survey.Model(window.config);
  survey.onComplete.add(surveyComplete);
  survey.applyTheme(THEME);

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

  survey.onTextMarkdown.add((_, options) => {
    const sanitized = DOMPurify.sanitize(marked.parse(options.text));
    if (sanitized.startsWith("<p>")) {
      options.html = sanitized.substring(3, sanitized.length - 5);
    } else {
      options.html = sanitized;
    }
  });

  survey.render(document.getElementById("survey"));
});
