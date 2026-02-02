/**
 * Drawing Layer Module for StarDeck
 *
 * Provides SVG-based drawing overlay for presenter annotations.
 * Uses percentage-based coordinates (0-100) for viewport independence.
 */

export class DrawingLayer {
    /**
     * Create a drawing layer attached to a container element.
     * @param {HTMLElement} container - The container to attach the SVG to
     */
    constructor(container) {
        this.container = container;
        this.svg = container.querySelector('.drawing-layer');

        if (!this.svg) {
            this.svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            this.svg.setAttribute('class', 'drawing-layer');
            this.svg.setAttribute('viewBox', '0 0 100 100');
            this.svg.setAttribute('preserveAspectRatio', 'none');
            container.appendChild(this.svg);
        }

        this.elements = new Map();
    }

    /**
     * Add a drawing element to the layer.
     * @param {Object} element - Element data with id, type, and rendering properties
     */
    addElement(element) {
        const svgElement = this.createSvgElement(element);
        if (svgElement) {
            svgElement.id = element.id;
            this.svg.appendChild(svgElement);
            this.elements.set(element.id, svgElement);
        }
    }

    /**
     * Remove an element by ID.
     * @param {string} id - Element ID to remove
     */
    removeElement(id) {
        const element = this.elements.get(id);
        if (element) {
            element.remove();
            this.elements.delete(id);
        }
    }

    /**
     * Clear all elements from the layer.
     */
    clear() {
        this.elements.forEach((el) => el.remove());
        this.elements.clear();
    }

    /**
     * Create an SVG element from element data.
     * @param {Object} element - Element data
     * @returns {SVGElement|null}
     */
    createSvgElement(element) {
        switch (element.type) {
            case 'pen':
                return this.createPathElement(element);
            case 'line':
            case 'arrow':
                return this.createLineElement(element);
            case 'rect':
                return this.createRectElement(element);
            case 'ellipse':
                return this.createEllipseElement(element);
            default:
                return null;
        }
    }

    /**
     * Create a path element for freehand drawing.
     * @param {Object} element - Pen element data with points array
     * @returns {SVGPathElement}
     */
    createPathElement(element) {
        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', this.pointsToPath(element.points));
        path.setAttribute('stroke', element.stroke_color);
        path.setAttribute('stroke-width', element.stroke_width);
        path.setAttribute('fill', 'none');
        path.setAttribute('stroke-linecap', 'round');
        path.setAttribute('stroke-linejoin', 'round');
        return path;
    }

    /**
     * Create a line element.
     * @param {Object} element - Line element data with start/end points
     * @returns {SVGLineElement}
     */
    createLineElement(element) {
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        const [start, end] = element.points;
        line.setAttribute('x1', start.x);
        line.setAttribute('y1', start.y);
        line.setAttribute('x2', end.x);
        line.setAttribute('y2', end.y);
        line.setAttribute('stroke', element.stroke_color);
        line.setAttribute('stroke-width', element.stroke_width);
        return line;
    }

    /**
     * Create a rectangle element.
     * @param {Object} element - Shape element data with x, y, width, height
     * @returns {SVGRectElement}
     */
    createRectElement(element) {
        const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        rect.setAttribute('x', element.x);
        rect.setAttribute('y', element.y);
        rect.setAttribute('width', element.width);
        rect.setAttribute('height', element.height);
        rect.setAttribute('stroke', element.stroke_color);
        rect.setAttribute('stroke-width', element.stroke_width);
        rect.setAttribute('fill', element.fill_color || 'none');
        return rect;
    }

    /**
     * Create an ellipse element.
     * @param {Object} element - Shape element data with x, y, width, height
     * @returns {SVGEllipseElement}
     */
    createEllipseElement(element) {
        const ellipse = document.createElementNS('http://www.w3.org/2000/svg', 'ellipse');
        ellipse.setAttribute('cx', element.x + element.width / 2);
        ellipse.setAttribute('cy', element.y + element.height / 2);
        ellipse.setAttribute('rx', element.width / 2);
        ellipse.setAttribute('ry', element.height / 2);
        ellipse.setAttribute('stroke', element.stroke_color);
        ellipse.setAttribute('stroke-width', element.stroke_width);
        ellipse.setAttribute('fill', element.fill_color || 'none');
        return ellipse;
    }

    /**
     * Convert an array of points to an SVG path string with smooth curves.
     * @param {Array} points - Array of {x, y, pressure} objects
     * @returns {string} SVG path d attribute
     */
    pointsToPath(points) {
        if (!points || points.length < 2) return '';

        let d = `M ${points[0].x} ${points[0].y}`;

        for (let i = 1; i < points.length - 1; i++) {
            const xc = (points[i].x + points[i + 1].x) / 2;
            const yc = (points[i].y + points[i + 1].y) / 2;
            d += ` Q ${points[i].x} ${points[i].y} ${xc} ${yc}`;
        }

        // Final line to last point
        const last = points[points.length - 1];
        d += ` L ${last.x} ${last.y}`;

        return d;
    }

    /**
     * Activate drawing mode (enables pointer events).
     */
    activate() {
        this.svg.classList.add('active');
    }

    /**
     * Deactivate drawing mode (disables pointer events).
     */
    deactivate() {
        this.svg.classList.remove('active');
    }
}
