export class CSSParser {
  constructor() {
    this.supportedProperties = [
      'color', 'background-color', 'font-size', 'font-family', 'font-weight',
      'margin', 'padding', 'border', 'width', 'height', 'display', 'position',
      'top', 'left', 'right', 'bottom', 'z-index', 'opacity', 'visibility',
      'text-align', 'line-height', 'text-decoration', 'cursor', 'overflow',
      'flex', 'grid', 'transform', 'transition', 'animation'
    ];
  }

  /**
   * Parse CSS content and extract rules
   * @param {string} cssContent
   * @returns {Object}
   */
  parse(cssContent) {
    const rules = this.extractRules(cssContent);
    const mediaQueries = this.extractMediaQueries(cssContent);
    const keyframes = this.extractKeyframes(cssContent);
    const imports = this.extractImports(cssContent);

    return {
      rules,
      mediaQueries,
      keyframes,
      imports,
      metadata: this.extractMetadata(cssContent)
    };
  }

  /**
   * Extract CSS rules
   * @param {string} cssContent
   * @returns {Array}
   */
  extractRules(cssContent) {
    const rules = [];
    // Remove comments first
    const cleanCSS = cssContent.replace(/\/\*[\s\S]*?\*\//g, '');
    
    // Match CSS rules (selector { properties })
    const ruleRegex = /([^{]+)\{([^}]+)\}/g;
    let match;

    while ((match = ruleRegex.exec(cleanCSS)) !== null) {
      const selector = match[1].trim();
      const properties = this.parseProperties(match[2]);
      
      rules.push({
        selector: selector,
        properties: properties,
        specificity: this.calculateSpecificity(selector)
      });
    }

    return rules;
  }

  /**
   * Parse CSS properties from a rule block
   * @param {string} propertiesString
   * @returns {Object}
   */
  parseProperties(propertiesString) {
    const properties = {};
    const propRegex = /([^:]+):([^;]+);?/g;
    let match;

    while ((match = propRegex.exec(propertiesString)) !== null) {
      const name = match[1].trim();
      const value = match[2].trim();
      properties[name] = value;
    }

    return properties;
  }

  /**
   * Extract media queries
   * @param {string} cssContent
   * @returns {Array}
   */
  extractMediaQueries(cssContent) {
    const mediaQueries = [];
    const mediaRegex = /@media\s+([^{]+)\{([\s\S]*?)\}/g;
    let match;

    while ((match = mediaRegex.exec(cssContent)) !== null) {
      const condition = match[1].trim();
      const content = match[2];
      const rules = this.extractRules(content);
      
      mediaQueries.push({
        condition: condition,
        rules: rules
      });
    }

    return mediaQueries;
  }

  /**
   * Extract keyframe animations
   * @param {string} cssContent
   * @returns {Array}
   */
  extractKeyframes(cssContent) {
    const keyframes = [];
    const keyframeRegex = /@keyframes\s+(\w+)\{([\s\S]*?)\}/g;
    let match;

    while ((match = keyframeRegex.exec(cssContent)) !== null) {
      const name = match[1];
      const content = match[2];
      const steps = this.extractKeyframeSteps(content);
      
      keyframes.push({
        name: name,
        steps: steps
      });
    }

    return keyframes;
  }

  /**
   * Extract keyframe steps
   * @param {string} keyframeContent
   * @returns {Array}
   */
  extractKeyframeSteps(keyframeContent) {
    const steps = [];
    const stepRegex = /(\d+%|from|to)\s*\{([^}]+)\}/g;
    let match;

    while ((match = stepRegex.exec(keyframeContent)) !== null) {
      const percentage = match[1];
      const properties = this.parseProperties(match[2]);
      
      steps.push({
        percentage: percentage,
        properties: properties
      });
    }

    return steps;
  }

  /**
   * Extract CSS imports
   * @param {string} cssContent
   * @returns {Array}
   */
  extractImports(cssContent) {
    const imports = [];
    const importRegex = /@import\s+["']([^"']+)["']/g;
    let match;

    while ((match = importRegex.exec(cssContent)) !== null) {
      imports.push({
        url: match[1]
      });
    }

    return imports;
  }

  /**
   * Calculate CSS selector specificity
   * @param {string} selector
   * @returns {number}
   */
  calculateSpecificity(selector) {
    let specificity = 0;
    
    // Count IDs
    const idMatches = selector.match(/#\w+/g);
    if (idMatches) specificity += idMatches.length * 1000;
    
    // Count classes and attributes
    const classMatches = selector.match(/\.\w+/g);
    if (classMatches) specificity += classMatches.length * 100;
    
    const attrMatches = selector.match(/\[[^\]]+\]/g);
    if (attrMatches) specificity += attrMatches.length * 100;
    
    // Count elements
    const elementMatches = selector.match(/\b\w+(?![.#\[])/g);
    if (elementMatches) specificity += elementMatches.length;
    
    return specificity;
  }

  /**
   * Extract metadata from CSS
   * @param {string} cssContent
   * @returns {Object}
   */
  extractMetadata(cssContent) {
    const metadata = {};
    
    // Extract charset
    const charsetMatch = cssContent.match(/@charset\s+["']([^"']+)["']/i);
    if (charsetMatch) {
      metadata.charset = charsetMatch[1];
    }

    // Count total rules
    const ruleCount = (cssContent.match(/\{[^}]*\}/g) || []).length;
    metadata.ruleCount = ruleCount;

    // Count media queries
    const mediaCount = (cssContent.match(/@media/g) || []).length;
    metadata.mediaQueryCount = mediaCount;

    // Count keyframes
    const keyframeCount = (cssContent.match(/@keyframes/g) || []).length;
    metadata.keyframeCount = keyframeCount;

    return metadata;
  }

  /**
   * Generate test cases based on parsed CSS
   * @param {Object} parsedData
   * @returns {Array}
   */
  generateTestCases(parsedData) {
    const testCases = [];

    // Test cases for responsive design
    parsedData.mediaQueries.forEach((mediaQuery, index) => {
      testCases.push({
        type: 'responsive_design',
        description: `Test responsive behavior for ${mediaQuery.condition}`,
        mediaQuery: {
          condition: mediaQuery.condition,
          ruleCount: mediaQuery.rules.length
        }
      });
    });

    // Test cases for animations
    parsedData.keyframes.forEach((keyframe, index) => {
      testCases.push({
        type: 'animation',
        description: `Test ${keyframe.name} animation`,
        keyframe: {
          name: keyframe.name,
          steps: keyframe.steps.length
        }
      });
    });

    // Test cases for critical CSS properties
    const criticalRules = parsedData.rules.filter(rule => 
      Object.keys(rule.properties).some(prop => 
        ['display', 'position', 'width', 'height', 'margin', 'padding'].includes(prop)
      )
    );

    criticalRules.forEach((rule, index) => {
      testCases.push({
        type: 'layout_validation',
        description: `Test layout for selector: ${rule.selector}`,
        rule: {
          selector: rule.selector,
          properties: Object.keys(rule.properties)
        }
      });
    });

    return testCases;
  }

  /**
   * Validate CSS syntax
   * @param {string} cssContent
   * @returns {Object}
   */
  validate(cssContent) {
    const errors = [];
    const warnings = [];

    // Check for unclosed braces
    const openBraces = (cssContent.match(/\{/g) || []).length;
    const closeBraces = (cssContent.match(/\}/g) || []).length;
    
    if (openBraces !== closeBraces) {
      errors.push('Unmatched braces detected');
    }

    // Check for semicolons
    const rules = this.extractRules(cssContent);
    rules.forEach((rule, index) => {
      const properties = Object.keys(rule.properties);
      properties.forEach(prop => {
        if (!prop.includes(':')) {
          warnings.push(`Rule ${index + 1}: Property "${prop}" missing colon`);
        }
      });
    });

    return {
      valid: errors.length === 0,
      errors: errors,
      warnings: warnings
    };
  }
}
