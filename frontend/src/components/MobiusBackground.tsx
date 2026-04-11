/**
 * 莫比乌斯环粒子背景组件
 * 使用Three.js实现3D莫比乌斯环粒子河流效果
 */
import { useEffect, useRef } from 'react'
import * as THREE from 'three'

export function MobiusBackground() {
  const containerRef = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<{
    scene: THREE.Scene
    camera: THREE.PerspectiveCamera
    renderer: THREE.WebGLRenderer
    particles: ParticleData[]
    mouse: { x: number; y: number; normalizedX: number; normalizedY: number }
    clock: THREE.Clock
    mobiusGroup: THREE.Group
    animationId: number
  } | null>(null)

  interface ParticleData {
    u: number
    v: number
    speed: number
    size: number
    opacity: number
    isBlue: boolean
    phase: number
    R: number
    w: number
    mesh: THREE.Mesh
  }

  useEffect(() => {
    if (!containerRef.current) return

    // 初始化场景
    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0xFFFFFF)

    // 相机设置
    const aspect = window.innerWidth / window.innerHeight
    const camera = new THREE.PerspectiveCamera(50, aspect, 0.1, 2000)
    camera.position.set(0, 15, 40)
    camera.lookAt(0, 0, 0)

    // 渲染器设置
    const renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true
    })
    renderer.setSize(window.innerWidth, window.innerHeight)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    containerRef.current.appendChild(renderer.domElement)

    // 莫比乌斯环组
    const mobiusGroup = new THREE.Group()
    scene.add(mobiusGroup)

    // 粒子数据数组
    const particles: ParticleData[] = []
    const clock = new THREE.Clock()
    const mouse = { x: 0, y: 0, normalizedX: 0, normalizedY: 0 }

    // 莫比乌斯环参数方程
    const getMobiusPoint = (u: number, v: number, R: number, w: number) => {
      const cosU = Math.cos(u)
      const sinU = Math.sin(u)
      const cosU2 = Math.cos(u / 2)
      const sinU2 = Math.sin(u / 2)

      const x = (R + v * w * cosU2) * cosU
      const y = (R + v * w * cosU2) * sinU
      const z = v * w * sinU2

      return new THREE.Vector3(x, y, z)
    }

    // 创建粒子
    const createParticles = () => {
      const R = 18
      const w = 6
      const particleCount = 500

      for (let i = 0; i < particleCount; i++) {
        const u = (i / particleCount) * Math.PI * 2
        const v = Math.random() * 2 - 1

        const particle: ParticleData = {
          u,
          v,
          speed: 0.3 + Math.random() * 0.2,
          size: 0.15 + Math.random() * 0.15,
          opacity: 0.2 + Math.random() * 0.25,
          isBlue: Math.random() < 0.7,
          phase: Math.random() * Math.PI * 2,
          R,
          w,
          mesh: null as unknown as THREE.Mesh
        }

        // 创建粒子几何体
        const geometry = new THREE.SphereGeometry(particle.size, 6, 6)
        const color = particle.isBlue ? 0x0071E3 : 0xF5E6D3
        const material = new THREE.MeshBasicMaterial({
          color,
          transparent: true,
          opacity: particle.opacity
        })

        particle.mesh = new THREE.Mesh(geometry, material)
        const pos = getMobiusPoint(particle.u, particle.v, R, w)
        particle.mesh.position.copy(pos)

        mobiusGroup.add(particle.mesh)
        particles.push(particle)
      }
    }

    // 创建河流线条
    const createRiverLines = () => {
      const R = 18
      const w = 6
      const lineCount = 12

      for (let i = 0; i < lineCount; i++) {
        const v = (i / (lineCount - 1)) * 2 - 1
        const points: THREE.Vector3[] = []
        const segments = 150

        for (let j = 0; j <= segments; j++) {
          const u = (j / segments) * Math.PI * 2
          const point = getMobiusPoint(u, v, R, w)
          points.push(point)
        }

        const geometry = new THREE.BufferGeometry().setFromPoints(points)
        const isBlue = i % 2 === 0
        const color = isBlue ? 0x0071E3 : 0xF5E6D3

        const material = new THREE.LineBasicMaterial({
          color,
          transparent: true,
          opacity: 0.12
        })

        const line = new THREE.Line(geometry, material)
        mobiusGroup.add(line)
      }
    }

    // 动画循环
    const animate = () => {
      const animationId = requestAnimationFrame(animate)
      const deltaTime = clock.getDelta()
      const elapsedTime = clock.getElapsedTime()

      // 莫比乌斯环旋转
      mobiusGroup.rotation.x = Math.sin(elapsedTime * 0.1) * 0.1
      mobiusGroup.rotation.y += 0.002
      mobiusGroup.rotation.z = Math.PI / 6

      // 呼吸效果
      const breathScale = 1 + Math.sin(elapsedTime * 0.5) * 0.02
      mobiusGroup.scale.set(breathScale, breathScale, breathScale)

      // 鼠标位置转换
      const mouseVector = new THREE.Vector3(
        mouse.normalizedX * 25,
        mouse.normalizedY * 15,
        10
      )

      // 更新粒子
      particles.forEach((particle) => {
        particle.u += particle.speed * deltaTime * 0.1
        if (particle.u > Math.PI * 2) particle.u -= Math.PI * 2

        let position = getMobiusPoint(particle.u, particle.v, particle.R, particle.w)

        // 波浪效果
        const wave = Math.sin(elapsedTime * 2 + particle.phase) * 0.5
        position.y += wave

        // 鼠标交互
        const worldPosition = position.clone()
        worldPosition.applyMatrix4(mobiusGroup.matrixWorld)

        const distanceToMouse = worldPosition.distanceTo(mouseVector)
        const interactionRadius = 8

        let targetOpacity = particle.opacity

        if (distanceToMouse < interactionRadius) {
          const force = (interactionRadius - distanceToMouse) / interactionRadius
          const avoidDir = position.clone().normalize()
          position.add(avoidDir.multiplyScalar(force * 2))
          targetOpacity = 0.7
        }

        const material = particle.mesh.material as THREE.MeshBasicMaterial
        material.opacity += (targetOpacity - material.opacity) * 0.1
        particle.mesh.position.copy(position)
      })

      renderer.render(scene, camera)

      // 保存animationId
      if (sceneRef.current) {
        sceneRef.current.animationId = animationId
      }
    }

    // 事件监听
    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight
      camera.updateProjectionMatrix()
      renderer.setSize(window.innerWidth, window.innerHeight)
    }

    const handleMouseMove = (e: MouseEvent) => {
      mouse.x = e.clientX
      mouse.y = e.clientY
      mouse.normalizedX = (e.clientX / window.innerWidth) * 2 - 1
      mouse.normalizedY = -(e.clientY / window.innerHeight) * 2 + 1
    }

    window.addEventListener('resize', handleResize)
    window.addEventListener('mousemove', handleMouseMove)

    // 初始化
    createParticles()
    createRiverLines()
    animate()

    // 保存引用
    sceneRef.current = {
      scene,
      camera,
      renderer,
      particles,
      mouse,
      clock,
      mobiusGroup,
      animationId: 0
    }

    // 清理函数
    return () => {
      window.removeEventListener('resize', handleResize)
      window.removeEventListener('mousemove', handleMouseMove)

      if (sceneRef.current) {
        cancelAnimationFrame(sceneRef.current.animationId)
      }

      // 清理Three.js资源
      particles.forEach((p) => {
        p.mesh.geometry.dispose()
        ;(p.mesh.material as THREE.Material).dispose()
      })

      mobiusGroup.children.forEach((child) => {
        if (child instanceof THREE.Line) {
          child.geometry.dispose()
          ;(child.material as THREE.Material).dispose()
        }
      })

      renderer.dispose()

      if (containerRef.current && renderer.domElement) {
        containerRef.current.removeChild(renderer.domElement)
      }
    }
  }, [])

  return (
    <div
      ref={containerRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        zIndex: -1,
        pointerEvents: 'none'
      }}
    />
  )
}
