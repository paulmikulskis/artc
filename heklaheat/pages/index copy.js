import Head from 'next/head'
import Image from 'next/image'
import styles from '../styles/Home.module.css'

import React, { useRef, useEffect, useState } from 'react'
import { Donut } from 'react-dial-knob'


import { TweenMax, Power3, gsap } from 'gsap'

import miles from '../public/mileseyes.png'

export default function Home() {

  const [value, setValue] = useState(0)
  // let milesLogo = useRef('hello')
  // console.log(milesLogo)

  // useEffect(() => {
  //   console.log(milesLogo)
  //   //milesLogo.style.display = 'none'
  //   gsap.to(
  //     milesLogo,
  //     {
  //       opacity: 1,
  //       y: -20,
  //       rotation: 360,
  //       ease: Power3.easeOut,
  //       duration: 2,
  //       delay: 1
  //     }
  //   )
  // }, [])

  return (
    <div className={styles.main}>
      <p>Hello World</p>
      {/* <div ref={el => {milesLogo = el}} style={{opacity: 0.3}}>
        <Image src={miles} />
      </div> */}

      <Donut
        diameter={200}
        min={0}
        max={100}
        step={1}
        value={value}
        theme={{
            donutColor: 'blue'
        }}
        onValueChange={setValue}
      >
      </Donut>

    </div>
  )
}
