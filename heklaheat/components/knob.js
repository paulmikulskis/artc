import React from "react";
import PropTypes from "prop-types";

function calcPointsCirc(cx, cy, rad, dashLength) {
  var n = rad / dashLength,
    alpha = (Math.PI * 2) / n,
    pointObj = {},
    points = [],
    i = -1;

  while (i < n) {
    var theta = alpha * i,
      theta2 = alpha * (i + 1);

    points.push({
      x: Math.cos(theta) * rad + cx,
      y: Math.sin(theta) * rad + cy,
      ex: Math.cos(theta2) * rad + cx,
      ey: Math.sin(theta2) * rad + cy
    });
    i += 2;
  }
  return points;
}

class Knob extends React.Component {
  static propTypes = {
    value: PropTypes.number.isRequired,
    onChange: PropTypes.func.isRequired,
    onChangeEnd: PropTypes.func,
    min: PropTypes.number,
    max: PropTypes.number,
    step: PropTypes.number,
    log: PropTypes.bool,
    width: PropTypes.number,
    height: PropTypes.number,
    thickness: PropTypes.number,
    lineCap: PropTypes.oneOf(["butt", "round"]),
    bgColor: PropTypes.string,
    fgColor: PropTypes.string,
    inputColor: PropTypes.string,
    font: PropTypes.string,
    fontWeight: PropTypes.string,
    clockwise: PropTypes.bool,
    cursor: PropTypes.oneOfType([PropTypes.number, PropTypes.bool]),
    stopper: PropTypes.bool,
    readOnly: PropTypes.bool,
    disableTextInput: PropTypes.bool,
    displayInput: PropTypes.bool,
    displayCustom: PropTypes.func,
    angleArc: PropTypes.number,
    angleOffset: PropTypes.number,
    disableMouseWheel: PropTypes.bool,
    title: PropTypes.string,
    className: PropTypes.string,
    canvasClassName: PropTypes.string
  };

  static defaultProps = {
    onChangeEnd: () => {},
    min: 0,
    max: 100,
    step: 1,
    log: false,
    width: 200,
    height: 200,
    thickness: 0.35,
    lineCap: "butt",
    bgColor: "#EEE",
    fgColor: "#EA2",
    inputColor: "",
    font: "Arial",
    fontWeight: "bold",
    clockwise: true,
    cursor: false,
    stopper: true,
    readOnly: false,
    disableTextInput: false,
    displayInput: true,
    angleArc: 360,
    angleOffset: 0,
    disableMouseWheel: false,
    className: null,
    canvasClassName: null
  };

  constructor(props) {
    super(props);
    this.w = this.props.width || 200;
    this.h = this.props.height || this.w;
    this.cursorExt = this.props.cursor === true ? 0.3 : this.props.cursor / 100;
    this.angleArc = (this.props.angleArc * Math.PI) / 180;
    this.angleOffset = (this.props.angleOffset * Math.PI) / 180;
    this.startAngle = 1.5 * Math.PI + this.angleOffset;
    this.endAngle = 1.5 * Math.PI + this.angleOffset + this.angleArc;
    this.digits =
      Math.max(
        String(Math.abs(this.props.min)).length,
        String(Math.abs(this.props.max)).length,
        2
      ) + 2;
    this.val = 0;
    this.coerce = 0;
  }

  componentDidMount() {
    this.drawCanvas();
    if (!this.props.readOnly) {
      this.canvasRef.addEventListener("touchstart", this.handleTouchStart, {
        passive: false
      });
    }
  }

  componentWillReceiveProps(nextProps) {
    if (nextProps.width && this.w !== nextProps.width) {
      this.w = nextProps.width;
    }
    if (nextProps.height && this.h !== nextProps.height) {
      this.h = nextProps.height;
    }
  }

  componentDidUpdate() {
    this.drawCanvas();
  }

  componentWillUnmount() {
    this.canvasRef.removeEventListener("touchstart", this.handleTouchStart);
  }

  getArcToValue = (v) => {
    let startAngle;
    let endAngle;
    const angle = !this.props.log
      ? ((v - this.props.min) * this.angleArc) /
        (this.props.max - this.props.min)
      : Math.log(Math.pow(v / this.props.min, this.angleArc)) /
        Math.log(this.props.max / this.props.min);
    if (!this.props.clockwise) {
      startAngle = this.endAngle + 0.00001;
      endAngle = startAngle - angle - 0.00001;
    } else {
      startAngle = this.startAngle - 0.00001;
      endAngle = startAngle + angle + 0.00001;
    }
    if (this.props.cursor) {
      startAngle = endAngle - this.cursorExt;
      endAngle += this.cursorExt;
    }
    return {
      startAngle,
      endAngle,
      acw: !this.props.clockwise && !this.props.cursor
    };
  };

  // Calculate ratio to scale canvas to avoid blurriness on HiDPI devices
  getCanvasScale = (ctx) => {
    const devicePixelRatio =
      window.devicePixelRatio ||
      window.screen.deviceXDPI / window.screen.logicalXDPI || // IE10
      1;
    const backingStoreRatio = ctx.webkitBackingStorePixelRatio || 1;
    return devicePixelRatio / backingStoreRatio;
  };

  coerceToStep = (v) => {
    let val = !this.props.log
      ? ~~((v < 0 ? -0.5 : 0.5) + v / this.props.step) * this.props.step
      : Math.pow(
          this.props.step,
          ~~(
            (Math.abs(v) < 1 ? -0.5 : 0.5) +
            Math.log(v) / Math.log(this.props.step)
          )
        );
    val = Math.max(Math.min(val, this.props.max), this.props.min);
    if (isNaN(val)) {
      val = 0;
    }
    this.coerce = Math.round(val * 1000) / 1000;
    return Math.round(val * 1000) / 1000;
  };

  eventToValue = (e) => {
    const bounds = this.canvasRef.getBoundingClientRect();
    const x = e.clientX - bounds.left;
    const y = e.clientY - bounds.top;
    let a = Math.atan2(x - this.w / 2, this.w / 2 - y) - this.angleOffset;
    if (!this.props.clockwise) {
      a = this.angleArc - a - 2 * Math.PI;
    }
    if (this.angleArc !== Math.PI * 2 && a < 0 && a > -0.5) {
      a = 0;
    } else if (a < 0) {
      a += Math.PI * 2;
    }
    const val = !this.props.log
      ? (a * (this.props.max - this.props.min)) / this.angleArc + this.props.min
      : Math.pow(this.props.max / this.props.min, a / this.angleArc) *
        this.props.min;
    this.val = val;
    return this.coerceToStep(val);
  };

  handleMouseDown = (e) => {
    this.props.onChange(this.eventToValue(e));
    document.addEventListener("mousemove", this.handleMouseMove);
    document.addEventListener("mouseup", this.handleMouseUp);
    document.addEventListener("keyup", this.handleEsc);
  };

  handleMouseMove = (e) => {
    e.preventDefault();
    this.props.onChange(this.eventToValue(e));
  };

  handleMouseUp = (e) => {
    this.props.onChangeEnd(this.eventToValue(e));
    document.removeEventListener("mousemove", this.handleMouseMove);
    document.removeEventListener("mouseup", this.handleMouseUp);
    document.removeEventListener("keyup", this.handleEsc);
  };

  handleTouchStart = (e) => {
    e.preventDefault();
    this.touchIndex = e.targetTouches.length - 1;
    this.props.onChange(this.eventToValue(e.targetTouches[this.touchIndex]));
    document.addEventListener("touchmove", this.handleTouchMove, {
      passive: false
    });
    document.addEventListener("touchend", this.handleTouchEnd);
    document.addEventListener("touchcancel", this.handleTouchEnd);
  };

  handleTouchMove = (e) => {
    e.preventDefault();
    this.props.onChange(this.eventToValue(e.targetTouches[this.touchIndex]));
  };

  handleTouchEnd = (e) => {
    this.props.onChangeEnd(this.eventToValue(e));
    document.removeEventListener("touchmove", this.handleTouchMove);
    document.removeEventListener("touchend", this.handleTouchEnd);
    document.removeEventListener("touchcancel", this.handleTouchEnd);
  };

  handleEsc = (e) => {
    if (e.keyCode === 27) {
      e.preventDefault();
      this.handleMouseUp();
    }
  };

  handleTextInput = (e) => {
    const val =
      Math.max(Math.min(+e.target.value, this.props.max), this.props.min) ||
      this.props.min;
    this.props.onChange(val);
  };

  handleWheel = (e) => {
    e.preventDefault();
    if (e.deltaX > 0 || e.deltaY > 0) {
      this.props.onChange(
        this.coerceToStep(
          !this.props.log
            ? this.props.value + this.props.step
            : this.props.value * this.props.step
        )
      );
    } else if (e.deltaX < 0 || e.deltaY < 0) {
      this.props.onChange(
        this.coerceToStep(
          !this.props.log
            ? this.props.value - this.props.step
            : this.props.value / this.props.step
        )
      );
    }
  };

  handleArrowKey = (e) => {
    if (e.keyCode === 37 || e.keyCode === 40) {
      e.preventDefault();
      this.props.onChange(
        this.coerceToStep(
          !this.props.log
            ? this.props.value - this.props.step
            : this.props.value / this.props.step
        )
      );
    } else if (e.keyCode === 38 || e.keyCode === 39) {
      e.preventDefault();
      this.props.onChange(
        this.coerceToStep(
          !this.props.log
            ? this.props.value + this.props.step
            : this.props.value * this.props.step
        )
      );
    }
  };

  inputStyle = () => ({
    width: `${(this.w / 2 + 4) >> 0}px`,
    height: `${(this.w / 3) >> 0}px`,
    position: "absolute",
    verticalAlign: "middle",
    marginTop: `${(this.w / 3) >> 0}px`,
    marginLeft: `-${((this.w * 3) / 4 + 2) >> 0}px`,
    border: 0,
    background: "none",
    font: `${this.props.fontWeight} ${(this.w / this.digits) >> 0}px ${
      this.props.font
    }`,
    textAlign: "center",
    color: this.props.inputColor || this.props.fgColor,
    padding: "0px",
    WebkitAppearance: "none"
  });

  drawCanvas() {
    const ctx = this.canvasRef.getContext("2d");
    const scale = this.getCanvasScale(ctx);
    this.canvasRef.width = this.w * scale; // clears the canvas
    this.canvasRef.height = this.h * scale;
    ctx.scale(scale, scale);
    this.xy = this.w / 2; // coordinates of canvas center
    this.lineWidth = this.xy * this.props.thickness;
    this.radius = this.xy - this.lineWidth / 2;
    ctx.lineWidth = this.lineWidth;
    ctx.lineCap = this.props.lineCap;
    // background arc
    /*ctx.beginPath();
    ctx.strokeStyle = this.props.bgColor;
    ctx.arc(
      this.xy,
      this.xy,
      this.radius,
      this.endAngle - 0.00001,
      this.startAngle + 0.00001,
      true
    );
    ctx.stroke();*/
    /**
 * 
    shadowOffsetX
    shadowOffsetY
    shadowColor
    shadowBlur
 */
    // dial background
    /*ctx.beginPath();
    ctx.strokeStyle = this.props.bgColor;
    ctx.lineWidth = this.lineWidth + 10;
    ctx.arc(this.xy, this.xy, this.radius - 10, 360, 0, true);
    ctx.stroke();*/
    ctx.save();
    // center
    ctx.beginPath();
    ctx.strokeStyle = "white";
    ctx.shadowColor = "rgba(0,0,0,0.25)";
    ctx.shadowBlur = 10;
    ctx.lineWidth = 0.000001;
    ctx.arc(this.xy, this.xy, this.radius - 23, 360, 0, true);
    var gradient = ctx.createRadialGradient(
      this.xy - this.w / 4,
      this.xy - 20,
      0,
      this.xy,
      this.xy,
      this.radius - 23
    );
    gradient.addColorStop(0.2, "#E1D1E9");
    gradient.addColorStop(1, "#F8AFAE");

    ctx.fillStyle = gradient;
    ctx.fill();
    ctx.stroke();
    ctx.shadowBlur = 0;

    // background
    ctx.beginPath();
    ctx.strokeStyle = "white";
    ctx.lineWidth = this.lineWidth;
    ctx.arc(
      this.xy,
      this.xy,
      this.radius - 30,
      this.endAngle - 0.00001,
      this.startAngle + 0.00001,
      true
    );
    ctx.stroke();

    // dashes
    ctx.beginPath();
    ctx.strokeStyle = "#E7D8E4";
    ctx.lineCap = "butt";
    ctx.setLineDash([2, 24]);
    ctx.beginPath();
    ctx.lineWidth = 2;
    ctx.arc(this.xy, this.xy, this.radius - 10, 0, Math.PI * 2);
    ctx.closePath();
    ctx.stroke();

    //ctx.setLineDash([0, 0]);
    ctx.restore();
    ctx.lineCap = this.props.lineCap;

    // foreground arc
    const a = this.getArcToValue(this.props.value);
    ctx.beginPath();
    ctx.lineWidth = this.lineWidth;
    ctx.strokeStyle = this.props.fgColor;
    if (this.props.cursor) {
      // ctx.arc(this.xy, this.xy, this.radius, a.startAngle, a.endAngle, a.acw);
      //ctx.arcTo(this.xy, this.xy, this.xy, this.xy, 10);
    } else {
      ctx.arc(
        this.xy,
        this.xy,
        this.radius - 30,
        a.startAngle,
        a.endAngle,
        a.acw
      );
    }
    ctx.stroke();

    // cursor
    ctx.beginPath();
    ctx.strokeStyle = "#F8AFAE";
    ctx.shadowColor = "rgba(0,0,0,0.25)";
    ctx.shadowBlur = 5;
    ctx.lineWidth = this.lineWidth + 10;
    ctx.arc(
      this.xy,
      this.xy,
      this.radius - 30,
      a.endAngle,
      a.endAngle + 0.0001,
      a.acw
    );
    ctx.stroke();

    /*
    // bacground
    ctx.restore();
    ctx.beginPath();
    ctx.strokeStyle = "white";
    ctx.shadowColor = "rgba(0,0,0,0.25)";
    ctx.shadowBlur = 1;
    ctx.lineWidth = 1;
    ctx.arc(this.xy, this.xy, this.radius, 360, 0, true);
    ctx.stroke();
    // ctx.closePath();
    ctx.fillStyle = "transparent";
    ctx.globalCompositeOperation = "destination-in";
    //ctx.fill();

    // always clean up -- set compsiting back to default
    ctx.globalCompositeOperation = "source-over";
    */
    ctx.shadowBlur = 0;
  }

  renderCenter = () => {
    const {
      displayCustom,
      displayInput,
      disableTextInput,
      readOnly,
      value
    } = this.props;

    if (displayInput) {
      return (
        <div>
          <input
          style={this.inputStyle()}
          type="text"
          value={value}
          onChange={this.handleTextInput}
          onKeyDown={this.handleArrowKey}
          readOnly={readOnly || disableTextInput}
        />
        </div>
      );
    } else if (displayCustom && typeof displayCustom === "function") {
      return displayCustom();
    }
    return null;
  };

  render() {
    const {
      canvasClassName,
      className,
      disableMouseWheel,
      readOnly,
      title,
      value
    } = this.props;

    return (
      <div
        className={className}
        style={{
          position: "relative",
          width: this.w,
          height: this.h,
          display: "inline-block",
          borderRadius: "100%",
          zIndex: 1,
          left: 0,
          right: 0,
          margin: "auto",
          display: "block"
        }}
        onWheel={readOnly || disableMouseWheel ? null : this.handleWheel}
      >
        <canvas
          ref={(ref) => {
            this.canvasRef = ref;
          }}
          className={canvasClassName}
          style={{
            width: "100%",
            height: "100%",
            borderRadius: "100%",
            boxShadow: "inset 0px 0px 1px 1px rgba(0,0,0,0.25)",
            background: "white",
            zIndex: 1
          }}
          onMouseDown={readOnly ? null : this.handleMouseDown}
          title={title ? `${title}: ${value}` : value}
        />
        {this.renderCenter()}
      </div>
    );
  }
}

export default Knob;
