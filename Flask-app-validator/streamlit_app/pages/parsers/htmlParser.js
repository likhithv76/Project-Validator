export class HTMLParser {
  constructor() {
    this.supportedElements = [
      'div', 'span', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'button', 'input', 'form', 'label', 'select', 'textarea',
      'a', 'img', 'ul', 'ol', 'li', 'table', 'tr', 'td', 'th',
      'header', 'footer', 'nav', 'main', 'section', 'article',
      'aside', 'figure', 'figcaption'
    ];
  }

  /**
   * Parse HTML content and extract elements
   * @param {string} htmlContent
   * @returns {Object}
   */
  parse(htmlContent) {
    const elements = this.extractElements(htmlContent);
    const forms = this.extractForms(htmlContent);
    const links = this.extractLinks(htmlContent);
    const images = this.extractImages(htmlContent);
    const scripts = this.extractScripts(htmlContent);
    const stylesheets = this.extractStylesheets(htmlContent);

    return {
      elements,
      forms,
      links,
      images,
      scripts,
      stylesheets,
      metadata: this.extractMetadata(htmlContent)
    };
  }

  /**
   * Extract HTML elements with their attributes
   * @param {string} htmlContent
   * @returns {Array}
   */
  extractElements(htmlContent) {
    const elements = [];
    const elementRegex = /<(\w+)([^>]*)>/gi;
    let match;

    while ((match = elementRegex.exec(htmlContent)) !== null) {
      const tagName = match[1].toLowerCase();
      const attributes = this.parseAttributes(match[2]);
      
      if (this.supportedElements.includes(tagName)) {
        elements.push({
          tag: tagName,
          attributes,
          id: attributes.id || null,
          class: attributes.class || null,
          text: this.extractElementText(htmlContent, match[0])
        });
      }
    }

    return elements;
  }

  /**
   * Extract form elements and their properties
   * @param {string} htmlContent
   * @returns {Array}
   */
  extractForms(htmlContent) {
    const forms = [];
    const formRegex = /<form([^>]*)>(.*?)<\/form>/gis;
    let match;

    while ((match = formRegex.exec(htmlContent)) !== null) {
      const formAttributes = this.parseAttributes(match[1]);
      const formContent = match[2];
      
      const inputs = this.extractFormInputs(formContent);
      
      forms.push({
        attributes: formAttributes,
        action: formAttributes.action || null,
        method: formAttributes.method || 'get',
        inputs
      });
    }

    return forms;
  }

  /**
   * Extract form inputs
   * @param {string} formContent
   * @returns {Array}
   */
  extractFormInputs(formContent) {
    const inputs = [];
    const inputRegex = /<(input|select|textarea)([^>]*)>/gi;
    let match;

    while ((match = inputRegex.exec(formContent)) !== null) {
      const inputType = match[1].toLowerCase();
      const attributes = this.parseAttributes(match[2]);
      
      inputs.push({
        type: inputType,
        attributes,
        name: attributes.name || null,
        id: attributes.id || null,
        required: attributes.required !== undefined,
        placeholder: attributes.placeholder || null
      });
    }

    return inputs;
  }

  /**
   * Extract links
   * @param {string} htmlContent
   * @returns {Array}
   */
  extractLinks(htmlContent) {
    const links = [];
    const linkRegex = /<a([^>]*)>(.*?)<\/a>/gi;
    let match;

    while ((match = linkRegex.exec(htmlContent)) !== null) {
      const attributes = this.parseAttributes(match[1]);
      const text = match[2].trim();
      
      links.push({
        href: attributes.href || null,
        text: text,
        target: attributes.target || null,
        attributes
      });
    }

    return links;
  }

  /**
   * Extract images
   * @param {string} htmlContent
   * @returns {Array}
   */
  extractImages(htmlContent) {
    const images = [];
    const imgRegex = /<img([^>]*)>/gi;
    let match;

    while ((match = imgRegex.exec(htmlContent)) !== null) {
      const attributes = this.parseAttributes(match[1]);
      
      images.push({
        src: attributes.src || null,
        alt: attributes.alt || null,
        width: attributes.width || null,
        height: attributes.height || null,
        attributes
      });
    }

    return images;
  }

  /**
   * Extract script tags
   * @param {string} htmlContent
   * @returns {Array}
   */
  extractScripts(htmlContent) {
    const scripts = [];
    const scriptRegex = /<script([^>]*)>(.*?)<\/script>/gis;
    let match;

    while ((match = scriptRegex.exec(htmlContent)) !== null) {
      const attributes = this.parseAttributes(match[1]);
      const content = match[2].trim();
      
      scripts.push({
        attributes,
        src: attributes.src || null,
        type: attributes.type || 'text/javascript',
        content: content || null
      });
    }

    return scripts;
  }

  /**
   * Extract stylesheet links
   * @param {string} htmlContent
   * @returns {Array}
   */
  extractStylesheets(htmlContent) {
    const stylesheets = [];
    const linkRegex = /<link([^>]*)>/gi;
    let match;

    while ((match = linkRegex.exec(htmlContent)) !== null) {
      const attributes = this.parseAttributes(match[1]);
      
      if (attributes.rel === 'stylesheet') {
        stylesheets.push({
          href: attributes.href || null,
          type: attributes.type || 'text/css',
          media: attributes.media || null,
          attributes
        });
      }
    }

    return stylesheets;
  }

  /**
   * Extract metadata from head section
   * @param {string} htmlContent
   * @returns {Object}
   */
  extractMetadata(htmlContent) {
    const metadata = {};
    
    // Extract title
    const titleMatch = htmlContent.match(/<title>(.*?)<\/title>/i);
    if (titleMatch) {
      metadata.title = titleMatch[1].trim();
    }

    // Extract meta tags
    const metaRegex = /<meta([^>]*)>/gi;
    let match;
    const metaTags = [];

    while ((match = metaRegex.exec(htmlContent)) !== null) {
      const attributes = this.parseAttributes(match[1]);
      metaTags.push(attributes);
    }

    metadata.metaTags = metaTags;
    return metadata;
  }

  /**
   * Parse HTML attributes string
   * @param {string} attrString
   * @returns {Object}
   */
  parseAttributes(attrString) {
    const attributes = {};
    const attrRegex = /(\w+)(?:=["']([^"']*)["'])?/gi;
    let match;

    while ((match = attrRegex.exec(attrString)) !== null) {
      const name = match[1].toLowerCase();
      const value = match[2] || true;
      attributes[name] = value;
    }

    return attributes;
  }

  /**
   * Extract text content from an element
   * @param {string} htmlContent
   * @param {string} elementTag
   * @returns {string}
   */
  extractElementText(htmlContent, elementTag) {
    const tagName = elementTag.match(/<(\w+)/i)?.[1];
    if (!tagName) return '';

    const closingTag = `</${tagName}>`;
    const startIndex = htmlContent.indexOf(elementTag);
    if (startIndex === -1) return '';

    const endIndex = htmlContent.indexOf(closingTag, startIndex);
    if (endIndex === -1) return '';

    const content = htmlContent.substring(startIndex + elementTag.length, endIndex);
    return content.trim();
  }

  /**
   * Generate test cases based on parsed HTML
   * @param {Object} parsedData
   * @returns {Array}
   */
  generateTestCases(parsedData) {
    const testCases = [];

    // Test cases for forms
    parsedData.forms.forEach((form, index) => {
      testCases.push({
        type: 'form_validation',
        description: `Test form ${index + 1} validation`,
        form: {
          action: form.action,
          method: form.method,
          inputs: form.inputs.map(input => ({
            name: input.name,
            type: input.type,
            required: input.required
          }))
        }
      });
    });

    // Test cases for links
    parsedData.links.forEach((link, index) => {
      if (link.href) {
        testCases.push({
          type: 'link_validation',
          description: `Test link ${index + 1} functionality`,
          link: {
            href: link.href,
            text: link.text,
            target: link.target
          }
        });
      }
    });

    // Test cases for images
    parsedData.images.forEach((img, index) => {
      testCases.push({
        type: 'image_validation',
        description: `Test image ${index + 1} loading`,
        image: {
          src: img.src,
          alt: img.alt
        }
      });
    });

    return testCases;
  }
}
