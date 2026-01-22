async function surveyComplete(survey) {
  try {
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
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = "survey-result";
      link.style.display = "none";
      document.body.appendChild(link);
      link.click();
      URL.revokeObjectURL(objectUrl);
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

marked.use(gfmHeadingId({
	prefix: "",
}));

DOMPurify.addHook('afterSanitizeAttributes', function (node) {

// set all elements owning target to target=_blank
  if ('target' in node) {
    node.setAttribute('target', '_blank');
    node.setAttribute('rel', 'noopener noreferrer');
  }
  // set non-HTML/MathML links to xlink:show=new
  if (!node.hasAttribute('target') && (node.hasAttribute('xlink:href') || node.hasAttribute('href'))) {
     node.setAttribute('xlink:show', 'new');
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

document.addEventListener("DOMContentLoaded", function () {
  survey.render(document.getElementById("survey"));
});
